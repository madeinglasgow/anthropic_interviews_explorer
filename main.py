import re
from contextlib import asynccontextmanager

from datasets import load_dataset
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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


transcripts_data = {}
transcript_ids = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcripts_data, transcript_ids

    print("Loading dataset from Hugging Face...")
    dataset = load_dataset("Anthropic/AnthropicInterviewer")

    for split_name in dataset.keys():
        for item in dataset[split_name]:
            transcript_id = item["transcript_id"]
            transcripts_data[transcript_id] = {
                "transcript_id": transcript_id,
                "split": split_name,
                "messages": parse_transcript(item["text"]),
            }

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
