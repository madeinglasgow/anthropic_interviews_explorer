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

# Run development server
uvicorn main:app --reload

# Access at http://localhost:8000
```

## Architecture

**Backend** (`main.py`): FastAPI server that loads the full dataset into memory on startup. Parses raw transcript text into structured messages using regex to split on "AI:" and "User:" markers.

**Frontend** (`static/`): Vanilla HTML/CSS/JS chat viewer styled to mimic DeepLearning.ai chatbot UI with Geist font.

**Data flow**: Dataset loads from Hugging Face → parsed into `transcripts_data` dict → served via REST API → rendered as chat bubbles in browser.

## API Endpoints

- `GET /api/transcripts?split=<workforce|creatives|scientists>` - List transcript metadata
- `GET /api/transcript/{transcript_id}` - Get single parsed transcript with messages array

## Dataset

- Source: `Anthropic/AnthropicInterviewer` on Hugging Face
- Splits: workforce (1,000), creatives (125), scientists (125)
- Fields: `transcript_id`, `text`, `split`
