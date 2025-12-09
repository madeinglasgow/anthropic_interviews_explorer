# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive viewer and analytics dashboard for the AnthropicInterviewer dataset (1,250 interview transcripts from Hugging Face). Displays AI-conducted interviews with professionals about their AI tool usage in a chat-style UI, plus aggregated insights via a Chart.js dashboard.

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

# Optional: Normalize fields for better dashboard aggregation
python normalize.py            # Normalize free-text fields to categories
python normalize.py --dry-run  # Preview unique values without normalizing

# Run development server
uvicorn main:app --reload

# Access at http://localhost:8000 (viewer) or http://localhost:8000/summary (dashboard)
```

## Architecture

**Data extraction** (`extract.py`): One-time script that downloads dataset from Hugging Face, uses Claude API to extract structured fields (job title, sentiment, industry, etc.), saves to `data/transcripts.json`.

**Normalization** (`normalize.py`): Optional post-processing script that maps free-text extracted values to standard categories using Claude API. Adds normalized fields alongside raw fields for better dashboard aggregation.

**Backend** (`main.py`): FastAPI server that loads pre-extracted data from `data/transcripts.json` into memory on startup. Serves both the transcript viewer and summary dashboard APIs.

**Frontend** (`static/`):
- `index.html`, `app.js`, `styles.css` - Chat-style transcript viewer with summary cards panel
- `summary.html`, `summary.js`, `summary.css` - Analytics dashboard with Chart.js visualizations

**Data flow**: HuggingFace → extract.py (one-time) → data/transcripts.json → [normalize.py (optional)] → main.py → REST API → browser

## API Endpoints

- `GET /api/transcripts?split=<workforce|creatives|scientists>` - List transcript metadata
- `GET /api/transcript/{transcript_id}` - Get single transcript with messages and extracted fields
- `GET /api/summary` - Aggregated statistics for dashboard (sentiment counts, top industries, tools, use cases, pain points, cross-tabulations, sample content)

## Pages

- `/` - Transcript viewer with chat display and summary cards
- `/summary` - Analytics dashboard with Chart.js visualizations

## Dataset

- Source: `Anthropic/AnthropicInterviewer` on Hugging Face
- Splits: workforce (1,000), creatives (125), scientists (125)
- Extracted fields: job_title, experience_level, sentiment, ai_tools_mentioned, industry, primary_use_cases, key_pain_points, last_project_summary
- Normalized fields (optional): industry_normalized, job_category, use_case_categories, pain_point_categories

## UI Design

- Styled to mimic DeepLearning.ai chatbot UI
- Geist font family
- Coral accent color (#fd4a61) for branding
- Summary cards use light coral background (#fde8eb)
- Summary panel uses scroll indicator button instead of scrollbar (arrow changes direction based on scroll position)

## Data Normalization

The `/api/summary` endpoint applies Python-based case normalization:
- Sentiment: lowercased (positive, negative, neutral, mixed)
- Experience level: lowercased (senior, mid-career, entry-level, executive)
- Industry: title-cased for display consistency

Optional LLM normalization (`normalize.py`) maps free-text fields to standard categories for cleaner aggregation.
