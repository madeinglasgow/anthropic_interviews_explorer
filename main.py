import json
import os
import random
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import numpy as np
import voyageai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

DATA_FILE = Path("data/transcripts.json")
EMBEDDINGS_FILE = Path("data/embeddings.json")

transcripts_data = {}
transcript_ids = []
embeddings_data = {}
embedding_model = ""
embedding_dimension = 0

# Lazy-loaded Voyage client
_vo_client = None


def get_voyage_client():
    global _vo_client
    if _vo_client is None:
        _vo_client = voyageai.Client()
    return _vo_client


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcripts_data, transcript_ids, embeddings_data, embedding_model, embedding_dimension

    if not DATA_FILE.exists():
        raise RuntimeError(
            f"{DATA_FILE} not found. Run 'python extract.py' first to generate the data."
        )

    print(f"Loading transcripts from {DATA_FILE}...")
    with open(DATA_FILE) as f:
        data = json.load(f)

    for transcript in data["transcripts"]:
        transcript_id = transcript["transcript_id"]
        transcripts_data[transcript_id] = transcript

    transcript_ids = sorted(transcripts_data.keys())
    print(f"Loaded {len(transcript_ids)} transcripts")

    # Load embeddings if available
    if EMBEDDINGS_FILE.exists():
        print(f"Loading embeddings from {EMBEDDINGS_FILE}...")
        with open(EMBEDDINGS_FILE) as f:
            emb_data = json.load(f)
        embeddings_data = emb_data["embeddings"]
        embedding_model = emb_data["model"]
        embedding_dimension = emb_data["dimension"]
        print(
            f"Loaded {len(embeddings_data)} embeddings (model: {embedding_model}, dim: {embedding_dimension})"
        )
    else:
        print("Warning: Embeddings file not found. Search will be disabled.")

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/transcripts")
async def list_transcripts(split: str | None = None):
    """List all transcript IDs with metadata."""
    results = []
    for tid in transcript_ids:
        data = transcripts_data[tid]
        if split is None or data["split"] == split:
            results.append(
                {
                    "transcript_id": tid,
                    "split": data["split"],
                    "message_count": len(data["messages"]),
                    "job_title": data.get("job_title"),
                    "industry": data.get("industry"),
                    "sentiment": data.get("sentiment"),
                }
            )
    return {"transcripts": results, "total": len(results)}


@app.get("/api/transcript/{transcript_id}")
async def get_transcript(transcript_id: str):
    """Get a single parsed transcript by ID."""
    if transcript_id not in transcripts_data:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcripts_data[transcript_id]


@app.get("/api/summary")
async def get_summary():
    """Get aggregated statistics for the dashboard."""
    transcripts = list(transcripts_data.values())

    # Sentiment counts (normalize case)
    sentiment_counts = Counter()
    for t in transcripts:
        sentiment = t.get("sentiment", "UNKNOWN")
        if sentiment and sentiment != "UNKNOWN":
            sentiment_counts[sentiment.lower()] += 1

    # Experience level counts (normalize case, include UNKNOWN)
    experience_counts = Counter()
    for t in transcripts:
        exp = t.get("experience_level", "UNKNOWN")
        if exp:
            experience_counts[exp.lower()] += 1
        else:
            experience_counts["unknown"] += 1

    # Split counts
    split_counts = Counter(t["split"] for t in transcripts)

    # Top industries (use normalized if available, fallback to raw with title case)
    industry_counts = Counter()
    for t in transcripts:
        industry = t.get("industry_normalized") or t.get("industry", "UNKNOWN")
        if industry and industry != "UNKNOWN":
            # Title case for consistency
            industry_counts[industry.title()] += 1

    # Top AI tools (flatten list field)
    tool_counts = Counter()
    for t in transcripts:
        tools = t.get("ai_tools_mentioned", [])
        for tool in tools:
            if tool and tool != "UNKNOWN":
                tool_counts[tool] += 1

    # Top use cases (use normalized if available)
    use_case_counts = Counter()
    for t in transcripts:
        cases = t.get("use_case_categories") or t.get("primary_use_cases", [])
        for case in cases:
            if case and case != "UNKNOWN":
                use_case_counts[case] += 1

    # Top pain points (use normalized if available)
    pain_point_counts = Counter()
    for t in transcripts:
        points = t.get("pain_point_categories") or t.get("key_pain_points", [])
        for point in points:
            if point and point != "UNKNOWN":
                pain_point_counts[point] += 1

    # Sentiment by split (normalize case)
    sentiment_by_split = {}
    for split in ["workforce", "creatives", "scientists"]:
        sentiment_by_split[split] = Counter()
    for t in transcripts:
        sentiment = t.get("sentiment", "UNKNOWN")
        if sentiment and sentiment != "UNKNOWN":
            sentiment_by_split[t["split"]][sentiment.lower()] += 1

    # Sentiment by experience level (normalize case, include UNKNOWN)
    sentiment_by_experience = {}
    for t in transcripts:
        exp = t.get("experience_level", "UNKNOWN")
        sentiment = t.get("sentiment", "UNKNOWN")
        if sentiment and sentiment != "UNKNOWN":
            exp_lower = exp.lower() if exp else "unknown"
            if exp_lower not in sentiment_by_experience:
                sentiment_by_experience[exp_lower] = Counter()
            sentiment_by_experience[exp_lower][sentiment.lower()] += 1

    # Sample projects
    projects = [
        t["last_project_summary"]
        for t in transcripts
        if t.get("last_project_summary") and t["last_project_summary"] != "UNKNOWN"
    ]
    sample_projects = random.sample(projects, min(5, len(projects))) if projects else []

    # Sample job titles
    job_titles = [
        t["job_title"]
        for t in transcripts
        if t.get("job_title") and t["job_title"] != "UNKNOWN"
    ]
    sample_job_titles = (
        random.sample(job_titles, min(10, len(job_titles))) if job_titles else []
    )

    return {
        "total_transcripts": len(transcripts),
        "sentiment_counts": dict(sentiment_counts),
        "experience_counts": dict(experience_counts),
        "split_counts": dict(split_counts),
        "top_industries": [
            {"name": name, "count": count}
            for name, count in industry_counts.most_common(10)
        ],
        "top_tools": [
            {"name": name, "count": count}
            for name, count in tool_counts.most_common(10)
        ],
        "top_use_cases": [
            {"name": name, "count": count}
            for name, count in use_case_counts.most_common(10)
        ],
        "top_pain_points": [
            {"name": name, "count": count}
            for name, count in pain_point_counts.most_common(10)
        ],
        "sentiment_by_split": {k: dict(v) for k, v in sentiment_by_split.items()},
        "sentiment_by_experience": {
            k: dict(v) for k, v in sentiment_by_experience.items()
        },
        "sample_projects": sample_projects,
        "sample_job_titles": sample_job_titles,
    }


class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0
    split: Optional[str] = None
    sentiment: Optional[str] = None
    industry: Optional[str] = None


@app.post("/api/search")
async def search_transcripts(request: SearchRequest):
    """Semantic search across transcripts."""
    if not embeddings_data:
        raise HTTPException(
            status_code=503, detail="Search not available - embeddings not loaded"
        )

    # Embed query
    vo = get_voyage_client()
    query_result = vo.embed(
        texts=[request.query], model=embedding_model, input_type="query"
    )
    query_embedding = query_result.embeddings[0]

    # Score all transcripts
    scores = []
    for tid, embedding in embeddings_data.items():
        # Apply filters
        transcript = transcripts_data.get(tid)
        if not transcript:
            continue
        if request.split and transcript["split"] != request.split:
            continue
        if (
            request.sentiment
            and transcript.get("sentiment", "").lower() != request.sentiment.lower()
        ):
            continue
        if (
            request.industry
            and request.industry.lower() not in transcript.get("industry", "").lower()
        ):
            continue

        score = cosine_similarity(query_embedding, embedding)
        scores.append((tid, score, transcript))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Paginate
    total = len(scores)
    paginated = scores[request.offset : request.offset + request.limit]

    # Build results
    results = []
    for tid, score, transcript in paginated:
        # Generate snippet from first few messages
        messages = transcript.get("messages", [])
        snippet_parts = []
        char_count = 0
        for msg in messages:
            if char_count > 200:
                break
            snippet_parts.append(msg["content"][:100])
            char_count += len(snippet_parts[-1])
        snippet = " ... ".join(snippet_parts)[:250]
        if len(snippet) == 250:
            snippet += "..."

        results.append(
            {
                "transcript_id": tid,
                "score": round(score, 4),
                "split": transcript["split"],
                "job_title": transcript.get("job_title"),
                "industry": transcript.get("industry"),
                "sentiment": transcript.get("sentiment"),
                "snippet": snippet,
            }
        )

    return {
        "query": request.query,
        "total": total,
        "offset": request.offset,
        "limit": request.limit,
        "results": results,
    }


@app.get("/")
async def root():
    return FileResponse("static/landing.html")


@app.get("/viewer")
async def viewer_page():
    return FileResponse("static/index.html")


@app.get("/summary")
async def summary_page():
    return FileResponse("static/summary.html")


@app.get("/search")
async def search_page():
    return FileResponse("static/search.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
