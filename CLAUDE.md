# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive viewer for the AnthropicInterviewer dataset (1,250 interview transcripts from Hugging Face). Displays AI-conducted interviews with professionals about their AI tool usage in a chat-style UI.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# One-time extraction (requires ANTHROPIC_API_KEY in .env)
python extract.py              # Extract all 1,250 transcripts
python extract.py --limit 10   # Test with first 10
python extract.py --resume     # Resume from checkpoint if interrupted

# Run development server
uvicorn main:app --reload

# Access at http://localhost:8000
```

## Architecture

**Data extraction** (`extract.py`): One-time script that downloads dataset from Hugging Face, uses Claude API to extract structured fields (job title, sentiment, industry, etc.), saves to `data/transcripts.json`.

**Backend** (`main.py`): FastAPI server that loads pre-extracted data from `data/transcripts.json` into memory on startup.

**Frontend** (`static/`): Vanilla HTML/CSS/JS chat viewer styled to mimic DeepLearning.ai chatbot UI with Geist font.

**Data flow**: HuggingFace → extract.py (one-time) → data/transcripts.json → main.py → REST API → browser

## API Endpoints

- `GET /api/transcripts?split=<workforce|creatives|scientists>` - List transcript metadata
- `GET /api/transcript/{transcript_id}` - Get single transcript with messages and extracted fields

## Dataset

- Source: `Anthropic/AnthropicInterviewer` on Hugging Face
- Splits: workforce (1,000), creatives (125), scientists (125)
- Extracted fields: job_title, experience_level, sentiment, ai_tools_mentioned, industry, primary_use_cases, key_pain_points, last_project_summary
