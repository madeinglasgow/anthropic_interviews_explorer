# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive viewer and analytics dashboard for the AnthropicInterviewer dataset (1,250 interview transcripts from Hugging Face). Displays AI-conducted interviews with professionals about their AI tool usage in a chat-style UI, plus aggregated insights via a Chart.js dashboard.

**Status**: Complete and deployed to Render.

## Deployment

- **Production URL**: Deployed on Render as a single web service
- **Deployment config**: `render.yaml` (Python 3.10, uvicorn)
- **Auto-deploy**: Pushes to `main` branch trigger automatic redeployment

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Access locally:
# - http://localhost:8000 (landing page)
# - http://localhost:8000/viewer (transcript viewer)
# - http://localhost:8000/search (semantic search)
# - http://localhost:8000/summary (insights dashboard)

# One-time extraction (requires ANTHROPIC_API_KEY in .env)
# Note: Data is already extracted and committed to repo - only needed if regenerating
python extract.py              # Extract all 1,250 transcripts
python extract.py --limit 10   # Test with first 10
python extract.py --resume     # Resume from checkpoint if interrupted

# Optional: Normalize fields for better dashboard aggregation
python normalize.py            # Normalize free-text fields to categories
python normalize.py --dry-run  # Preview unique values without normalizing

# One-time embedding generation (requires VOYAGE_API_KEY in .env)
# Note: Embeddings are already generated and committed to repo - only needed if regenerating
python embed.py                # Embed all 1,250 transcripts
python embed.py --limit 10     # Test with first 10
python embed.py --resume       # Resume from checkpoint if interrupted
```

## Architecture

**Data extraction** (`extract.py`): One-time script that downloads dataset from Hugging Face, uses Claude API to extract structured fields (job title, sentiment, industry, etc.), saves to `data/transcripts.json`.

**Normalization** (`normalize.py`): Optional post-processing script that maps free-text extracted values to standard categories using Claude API. Adds normalized fields alongside raw fields for better dashboard aggregation.

**Embedding generation** (`embed.py`): One-time script that generates Voyage AI embeddings for all transcripts. Composes embedding text from full transcript + metadata fields, saves to `data/embeddings.json`. Supports checkpoint/resume for interrupted runs.

**Backend** (`main.py`): FastAPI server that loads pre-extracted data from `data/transcripts.json` and embeddings from `data/embeddings.json` into memory on startup. Serves the transcript viewer, search, and summary dashboard APIs.

**Frontend** (`static/`):
- `landing.html`, `landing.css` - Landing page with dataset overview and navigation
- `index.html`, `app.js`, `styles.css` - Chat-style transcript viewer with summary cards panel
- `search.html`, `search.js`, `search.css` - Semantic search page with filters and pagination
- `summary.html`, `summary.js`, `summary.css` - Analytics dashboard with Chart.js visualizations

**Data flow**: HuggingFace → extract.py (one-time) → data/transcripts.json → [normalize.py (optional)] → main.py → REST API → browser

## API Endpoints

- `GET /api/transcripts?split=<workforce|creatives|scientists>` - List transcript metadata
- `GET /api/transcript/{transcript_id}` - Get single transcript with messages and extracted fields
- `POST /api/search` - Semantic search with query, filters (split, sentiment, industry), pagination
- `GET /api/summary` - Aggregated statistics for dashboard (sentiment counts, top industries, tools, use cases, pain points, cross-tabulations, sample content)

## Pages

- `/` - Landing page with dataset context, key findings, and navigation
- `/viewer` - Transcript viewer with chat display and summary cards (supports `?id=transcript_id` deep linking)
- `/search` - Semantic search with natural language queries, filters, and clickable results
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
- Transcript viewer includes "View chat #" input for direct navigation to any transcript
- Dashboard includes shuffle buttons on sample content cards to load random samples
- Search results show relevance scores as percentages, clickable cards link to viewer

## Semantic Search

- Uses Voyage AI embeddings (`voyage-3` model, 1024 dimensions)
- Pre-computed transcript embeddings stored in `data/embeddings.json`
- Query embeddings generated at runtime (requires `VOYAGE_API_KEY`)
- Results ranked by cosine similarity, top 20 returned per page
- Supports filtering by split, sentiment, and industry

## Data Normalization

The `/api/summary` endpoint applies Python-based case normalization:
- Sentiment: lowercased (positive, negative, neutral, mixed)
- Experience level: lowercased, includes "unknown" for missing values (senior, mid-career, entry-level, executive, unknown)
- Industry: title-cased for display consistency

Optional LLM normalization (`normalize.py`) maps free-text fields to standard categories for cleaner aggregation.
