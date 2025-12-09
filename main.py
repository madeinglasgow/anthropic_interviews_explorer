import json
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


@app.get("/")
async def root():
    return FileResponse("static/index.html")


app.mount("/static", StaticFiles(directory="static"), name="static")
