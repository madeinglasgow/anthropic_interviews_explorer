"""
One-time extraction script: Downloads dataset from Hugging Face,
extracts structured fields using Claude API, saves to local JSON.

Usage:
    python extract.py                    # Extract all transcripts
    python extract.py --limit 10         # Extract first 10 (for testing)
    python extract.py --resume           # Resume from last checkpoint
"""

import argparse
import json
import os
import re
from pathlib import Path

import anthropic
from datasets import load_dataset
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
OUTPUT_FILE = DATA_DIR / "transcripts.json"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"

EXTRACTION_PROMPT = """\
Analyze this interview transcript and extract the following fields.
If you cannot determine a field from the conversation, write "UNKNOWN".

Fields to extract:
1. job_title: The participant's job title or role
2. experience_level: Their self-reported career experience level (e.g., "entry-level", "mid-career", "senior", "executive"). This is about their career experience, NOT their AI skill level.
3. sentiment: Overall sentiment toward AI tools (one of: "positive", "neutral", "negative", "mixed")
4. ai_tools_mentioned: List of specific AI tools mentioned (e.g., ["Claude", "ChatGPT", "Grammarly"])
5. industry: The industry or domain they work in
6. primary_use_cases: Main ways they use AI in their work (list of brief descriptions)
7. key_pain_points: Main frustrations or challenges with AI tools (list of brief descriptions)
8. last_project_summary: Brief summary of a recent AI project or use case they described (1-2 sentences)

Respond with valid JSON only, no other text:
{
  "job_title": "...",
  "experience_level": "...",
  "sentiment": "...",
  "ai_tools_mentioned": ["...", "..."],
  "industry": "...",
  "primary_use_cases": ["...", "..."],
  "key_pain_points": ["...", "..."],
  "last_project_summary": "..."
}

TRANSCRIPT:
"""


def parse_transcript(text: str) -> list[dict]:
    """Parse transcript into list of {role, content} messages."""
    messages = []
    parts = re.split(r"(AI:|User:)", text)

    current_role = None
    for part in parts:
        part = part.strip()
        if part == "AI:":
            current_role = "ai"
        elif part == "User:":
            current_role = "user"
        elif current_role and part:
            messages.append({"role": current_role, "content": part})

    return messages


def extract_fields(client: anthropic.Anthropic, transcript_text: str) -> dict:
    """Extract structured fields from a transcript using Claude."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT + transcript_text,
            }
        ],
    )

    response_text = response.content[0].text.strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError(f"Could not parse JSON from response: {response_text}")


def load_checkpoint() -> set:
    """Load set of already-processed transcript IDs."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(processed_ids: set):
    """Save checkpoint of processed transcript IDs."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(list(processed_ids), f)


def load_existing_data() -> dict:
    """Load existing extracted data if resuming."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
            return {t["transcript_id"]: t for t in data["transcripts"]}
    return {}


def main():
    parser = argparse.ArgumentParser(description="Extract fields from interview transcripts")
    parser.add_argument("--limit", type=int, help="Limit number of transcripts to process")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    client = anthropic.Anthropic()

    print("Loading dataset from Hugging Face...")
    dataset = load_dataset("Anthropic/AnthropicInterviewer")

    all_items = []
    for split_name in dataset.keys():
        for item in dataset[split_name]:
            all_items.append((split_name, item))

    all_items.sort(key=lambda x: x[1]["transcript_id"])

    if args.limit:
        all_items = all_items[: args.limit]

    processed_ids = load_checkpoint() if args.resume else set()
    transcripts_data = load_existing_data() if args.resume else {}

    print(f"Total transcripts: {len(all_items)}")
    if args.resume:
        print(f"Already processed: {len(processed_ids)}")

    for i, (split_name, item) in enumerate(all_items):
        transcript_id = item["transcript_id"]

        if transcript_id in processed_ids:
            continue

        print(f"[{i + 1}/{len(all_items)}] Extracting {transcript_id}...")

        try:
            extracted = extract_fields(client, item["text"])

            transcripts_data[transcript_id] = {
                "transcript_id": transcript_id,
                "split": split_name,
                "messages": parse_transcript(item["text"]),
                **extracted,
            }

            processed_ids.add(transcript_id)

            if (i + 1) % 10 == 0:
                save_checkpoint(processed_ids)
                output = {"transcripts": list(transcripts_data.values())}
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(output, f, indent=2)
                print(f"  Checkpoint saved ({len(processed_ids)} transcripts)")

        except Exception as e:
            print(f"  Error extracting {transcript_id}: {e}")
            continue

    output = {"transcripts": list(transcripts_data.values())}
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    print(f"\nDone! Extracted {len(transcripts_data)} transcripts to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
