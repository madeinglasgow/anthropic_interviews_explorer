"""
One-time embedding generation script: Loads transcripts from data/transcripts.json,
generates embeddings using Voyage AI, saves to data/embeddings.json.

Usage:
    python embed.py                    # Embed all transcripts
    python embed.py --limit 10         # Embed first 10 (for testing)
    python embed.py --resume           # Resume from checkpoint
    python embed.py --model voyage-3   # Specify model (default: voyage-3)
"""

import argparse
import json
import time
from pathlib import Path

import voyageai
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
INPUT_FILE = DATA_DIR / "transcripts.json"
OUTPUT_FILE = DATA_DIR / "embeddings.json"
CHECKPOINT_FILE = DATA_DIR / "embeddings_checkpoint.json"

# Batch size - increase to 128 once rate limits are unlocked
BATCH_SIZE = 64
RETRY_DELAY = 25  # seconds to wait on rate limit
DELAY_BETWEEN_BATCHES = 1  # seconds between requests


def compose_embedding_text(transcript: dict) -> str:
    """Compose text for embedding with labeled sections."""
    # Full transcript with role labels
    messages = transcript.get("messages", [])
    transcript_text = "\n".join(
        [f"{msg['role'].upper()}: {msg['content']}" for msg in messages]
    )

    # Collect metadata fields
    job_title = transcript.get("job_title", "")
    industry = transcript.get("industry", "")
    tools = transcript.get("ai_tools_mentioned", [])
    use_cases = transcript.get("primary_use_cases", [])
    pain_points = transcript.get("key_pain_points", [])
    project_summary = transcript.get("last_project_summary", "")

    # Build sections with labels
    sections = [
        f"INTERVIEW TRANSCRIPT:\n{transcript_text}",
    ]

    if job_title and job_title != "UNKNOWN":
        sections.append(f"JOB TITLE: {job_title}")
    if industry and industry != "UNKNOWN":
        sections.append(f"INDUSTRY: {industry}")
    if tools:
        sections.append(f"AI TOOLS: {', '.join(tools)}")
    if use_cases:
        sections.append(f"USE CASES: {', '.join(use_cases)}")
    if pain_points:
        sections.append(f"PAIN POINTS: {', '.join(pain_points)}")
    if project_summary and project_summary != "UNKNOWN":
        sections.append(f"PROJECT SUMMARY: {project_summary}")

    return "\n\n".join(sections)


def load_transcripts() -> list[dict]:
    """Load transcripts from JSON file."""
    with open(INPUT_FILE) as f:
        return json.load(f)["transcripts"]


def load_checkpoint() -> tuple[set, dict]:
    """Load checkpoint with processed IDs and existing embeddings."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)
            return set(data.get("processed_ids", [])), data.get("embeddings", {})
    return set(), {}


def save_checkpoint(processed_ids: set, embeddings: dict, model: str, dimension: int):
    """Save checkpoint."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(
            {
                "processed_ids": list(processed_ids),
                "embeddings": embeddings,
                "model": model,
                "dimension": dimension,
            },
            f,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for interview transcripts"
    )
    parser.add_argument("--limit", type=int, help="Limit transcripts to process")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--model", default="voyage-3", help="Voyage model to use")
    args = parser.parse_args()

    vo = voyageai.Client()  # Uses VOYAGE_API_KEY env var

    transcripts = load_transcripts()

    if args.limit:
        transcripts = transcripts[: args.limit]

    processed_ids, embeddings = load_checkpoint() if args.resume else (set(), {})

    # Filter unprocessed transcripts
    to_process = [t for t in transcripts if t["transcript_id"] not in processed_ids]

    print(f"Model: {args.model}")
    print(
        f"Total: {len(transcripts)}, Already processed: {len(processed_ids)}, To process: {len(to_process)}"
    )

    if not to_process:
        print("Nothing to process!")
        return

    dimension = None

    # Process in batches
    for i in range(0, len(to_process), BATCH_SIZE):
        batch = to_process[i : i + BATCH_SIZE]
        texts = [compose_embedding_text(t) for t in batch]
        ids = [t["transcript_id"] for t in batch]

        print(f"[{i + len(batch)}/{len(to_process)}] Embedding batch of {len(batch)}...")

        # Retry loop for rate limits
        max_retries = 5
        for attempt in range(max_retries):
            try:
                result = vo.embed(texts=texts, model=args.model, input_type="document")
                break
            except voyageai.error.RateLimitError as e:
                if attempt < max_retries - 1:
                    print(f"  Rate limited, waiting {RETRY_DELAY}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(RETRY_DELAY)
                else:
                    raise e

        for tid, embedding in zip(ids, result.embeddings):
            embeddings[tid] = embedding
            processed_ids.add(tid)

        # Get dimension from first result
        if dimension is None:
            dimension = len(result.embeddings[0])
            print(f"Embedding dimension: {dimension}")

        # Checkpoint every batch
        save_checkpoint(processed_ids, embeddings, args.model, dimension)
        print(f"  Checkpoint saved ({len(processed_ids)} total)")

        # Delay between batches to respect rate limits
        if i + BATCH_SIZE < len(to_process):
            time.sleep(DELAY_BETWEEN_BATCHES)

    # Save final output
    output = {
        "model": args.model,
        "dimension": dimension,
        "count": len(embeddings),
        "embeddings": embeddings,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f)

    # Clean up checkpoint
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    print(f"\nDone! Saved {len(embeddings)} embeddings to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
