# Anthropic Interviewer Dataset Explorer

Interactive viewer and analytics dashboard for the [AnthropicInterviewer dataset](https://huggingface.co/datasets/Anthropic/AnthropicInterviewer) — 1,250 AI-conducted interviews about how professionals use AI in their work.

## Features

- **Transcript Viewer**: Browse individual interview conversations in a chat-style UI with extracted metadata and AI-generated summaries
- **Insights Dashboard**: Explore aggregated statistics, sentiment analysis, and trends across all interviews using Chart.js visualizations
- **Enhanced Metadata**: AI-extracted fields including job title, industry, experience level, sentiment, AI tools mentioned, use cases, and pain points

## About the Dataset

The [Anthropic Interviewer](https://www.anthropic.com/research/anthropic-interviewer) is an AI-powered tool that conducts automated interviews at scale while maintaining user privacy. This dataset includes:

| Split | Count |
|-------|-------|
| General Workforce | 1,000 |
| Scientists | 125 |
| Creatives | 125 |
| **Total** | **1,250** |

### Key Findings

- **General Workforce**: 86% reported time savings, 65% expressed satisfaction with AI's workplace role
- **Creatives**: 97% reported time savings, 68% noted quality improvements
- **Scientists**: 91% wanted more AI assistance, 79% cited reliability concerns

## What This Explorer Adds

The original Anthropic dataset contains raw interview transcripts. This explorer enhances the data with AI-extracted metadata for each interview:

- Job title and industry
- Experience level (entry-level, mid-career, senior, executive)
- Overall sentiment toward AI tools
- AI tools mentioned during the interview
- Primary use cases for AI in their work
- Key pain points and challenges
- Project summaries describing recent AI-assisted work

These fields are normalized into standard categories, enabling aggregated analysis and visualization.

## Local Development

### Prerequisites

- Python 3.10+
- [Anthropic API key](https://console.anthropic.com/) (only needed if regenerating data)

### Setup

```bash
# Clone the repository
git clone https://github.com/madeinglasgow/anthropic_interviews_explorer.git
cd anthropic_interviews_explorer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload
```

Visit http://localhost:8000 to view the app.

### Regenerating Data (Optional)

The repository includes pre-extracted transcript data. To regenerate from scratch:

```bash
# Set your Anthropic API key
echo "ANTHROPIC_API_KEY=your-key-here" > .env

# Extract all transcripts (takes ~2 hours, uses Claude API)
python extract.py

# Optional: Normalize fields for better aggregation
python normalize.py
```

## Project Structure

```
├── main.py              # FastAPI server
├── extract.py           # One-time data extraction script
├── normalize.py         # Optional field normalization script
├── data/
│   └── transcripts.json # Pre-extracted transcript data (1,250 interviews)
├── static/
│   ├── landing.html/css # Landing page
│   ├── index.html       # Transcript viewer
│   ├── app.js           # Viewer JavaScript
│   ├── summary.html/css # Insights dashboard
│   ├── summary.js       # Dashboard JavaScript
│   └── styles.css       # Shared styles
└── requirements.txt
```

## API Endpoints

- `GET /api/transcripts?split=<workforce|creatives|scientists>` - List transcript metadata
- `GET /api/transcript/{transcript_id}` - Get single transcript with messages
- `GET /api/summary` - Aggregated statistics for dashboard

## Data Sources

- Dataset: [Anthropic/AnthropicInterviewer](https://huggingface.co/datasets/Anthropic/AnthropicInterviewer) on Hugging Face
- Research: [Anthropic Interviewer Blog Post](https://www.anthropic.com/research/anthropic-interviewer)

## License

This project is for educational and research purposes. The underlying interview data is provided by Anthropic under their dataset license.
