import json
import random
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DATA_FILE = Path("data/transcripts.json")

transcripts_data = {}
transcript_ids = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcripts_data, transcript_ids

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

    # Experience level counts (normalize case)
    experience_counts = Counter()
    for t in transcripts:
        exp = t.get("experience_level", "UNKNOWN")
        if exp and exp != "UNKNOWN":
            experience_counts[exp.lower()] += 1

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

    # Sentiment by experience level (normalize case)
    sentiment_by_experience = {}
    for t in transcripts:
        exp = t.get("experience_level", "UNKNOWN")
        sentiment = t.get("sentiment", "UNKNOWN")
        if exp and exp != "UNKNOWN" and sentiment and sentiment != "UNKNOWN":
            exp_lower = exp.lower()
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


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/summary")
async def summary_page():
    return FileResponse("static/summary.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
