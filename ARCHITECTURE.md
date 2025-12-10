# Architecture Deep Dive

A technical guide for understanding how this application works and the reasoning behind its design choices.

## Table of Contents

1. [The Single-Service Architecture](#the-single-service-architecture)
2. [How the Pieces Fit Together](#how-the-pieces-fit-together)
3. [The Data Pipeline](#the-data-pipeline)
4. [Frontend-Backend Communication](#frontend-backend-communication)
5. [Semantic Search Implementation](#semantic-search-implementation)
6. [Key Design Decisions](#key-design-decisions)
7. [What We Didn't Do (And Why)](#what-we-didnt-do-and-why)
8. [Ideas for Further Learning](#ideas-for-further-learning)

---

## The Single-Service Architecture

You expected to need two services (frontend + backend), but we deployed just one. Here's why:

### Traditional Two-Service Setup

In many modern web applications, you'll see:

```
┌─────────────────┐     ┌─────────────────┐
│  Frontend       │     │  Backend        │
│  (React, Vue)   │────▶│  (Node, Python) │
│  Port 3000      │     │  Port 8000      │
│  Serves HTML/JS │     │  Serves API     │
└─────────────────┘     └─────────────────┘
```

This separation makes sense when:
- Frontend needs its own build process (React, Vue, Webpack)
- Teams are split between frontend and backend developers
- You want to scale frontend and backend independently
- You're using server-side rendering (Next.js, Nuxt)

### Our Single-Service Setup

```
┌────────────────────────────────────────┐
│  FastAPI Server (main.py)              │
│                                        │
│  ┌──────────────┐  ┌────────────────┐  │
│  │ Static Files │  │ API Endpoints  │  │
│  │ /static/*    │  │ /api/*         │  │
│  │ HTML, JS, CSS│  │ JSON responses │  │
│  └──────────────┘  └────────────────┘  │
│                                        │
│  Port 8000                             │
└────────────────────────────────────────┘
```

This works because:

1. **No build step needed**: Our frontend is "vanilla" HTML, CSS, and JavaScript. No React, no Webpack, no npm build. The browser runs our JS files directly.

2. **FastAPI serves static files**: This line in `main.py` tells FastAPI to serve anything in the `static/` folder:
   ```python
   app.mount("/static", StaticFiles(directory="static"), name="static")
   ```

3. **HTML pages are just file responses**: Each page is served directly:
   ```python
   @app.get("/viewer")
   async def viewer_page():
       return FileResponse("static/index.html")
   ```

4. **Same-origin requests**: Since frontend and backend share the same origin (domain + port), we avoid CORS issues entirely.

### When You'd Need Two Services

You'd split them if:
- Using React/Vue/Svelte (need `npm run build`)
- Frontend needs CDN deployment for global performance
- Different scaling requirements (10x frontend load vs backend)
- Microservices architecture with multiple backends

---

## How the Pieces Fit Together

### File Structure Explained

```
anthropic_interview/
├── main.py              # The "brain" - FastAPI server
├── extract.py           # One-time script: downloads + processes raw data
├── normalize.py         # One-time script: standardizes categories
├── embed.py             # One-time script: generates search embeddings
├── requirements.txt     # Python dependencies
├── render.yaml          # Deployment configuration
├── data/
│   ├── transcripts.json # The processed interview data
│   └── embeddings.json  # Pre-computed vectors for search
└── static/
    ├── index.html       # Transcript viewer page
    ├── app.js           # Transcript viewer logic
    ├── styles.css       # Transcript viewer styles
    ├── search.html      # Search page
    ├── search.js        # Search logic
    ├── search.css       # Search styles
    ├── summary.html     # Dashboard page
    ├── summary.js       # Dashboard logic (Chart.js)
    ├── summary.css      # Dashboard styles
    ├── landing.html     # Homepage
    └── landing.css      # Homepage styles
```

### The Server: main.py

Think of `main.py` as a receptionist that:
1. Loads all data into memory when starting up
2. Listens for requests
3. Routes each request to the right handler
4. Returns the appropriate response

```python
# Startup: Load everything into memory
@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcripts, transcripts_by_id, embeddings_data
    # Load JSON files once, keep in memory
    with open("data/transcripts.json") as f:
        data = json.load(f)
        transcripts = data["transcripts"]
    # ... same for embeddings
    yield  # Server runs here
    # Cleanup would go here (we don't need any)
```

**Why load into memory?**
- 1,250 transcripts = ~15MB in memory
- Reading from memory: microseconds
- Reading from disk: milliseconds
- For small datasets, this is the simplest approach

### The Frontend Files

Each page is self-contained:

```
landing.html ─────────────────────────────┐
  └── landing.css (styles)                │
                                          │
index.html (viewer) ──────────────────────┤
  ├── styles.css (styles)                 │──▶ All served by
  └── app.js (logic)                      │    FastAPI from
                                          │    /static/
search.html ──────────────────────────────┤
  ├── search.css (styles)                 │
  └── search.js (logic)                   │
                                          │
summary.html ─────────────────────────────┘
  ├── summary.css (styles)
  └── summary.js (logic + Chart.js)
```

Each `.js` file:
1. Waits for the page to load
2. Fetches data from `/api/*` endpoints
3. Manipulates the DOM to display results

---

## The Data Pipeline

Data flows through several transformation stages:

```
┌─────────────────────┐
│ Hugging Face        │  Raw dataset: 1,250 interview transcripts
│ (Cloud)             │  Just conversation messages, no metadata
└──────────┬──────────┘
           │ python extract.py (one-time)
           │ Uses Claude API to extract structured fields
           ▼
┌─────────────────────┐
│ data/transcripts.json│  Enriched data: messages + job_title,
│ (Local file)        │  sentiment, industry, tools, etc.
└──────────┬──────────┘
           │ python normalize.py (optional, one-time)
           │ Standardizes free-text to categories
           ▼
┌─────────────────────┐
│ data/transcripts.json│  Normalized: "Software Dev" → "Technology"
│ (Updated)           │
└──────────┬──────────┘
           │ python embed.py (one-time)
           │ Uses Voyage AI to create vector embeddings
           ▼
┌─────────────────────┐
│ data/embeddings.json │  1,250 vectors (1024 dimensions each)
│ (New file)          │  For semantic search
└──────────┬──────────┘
           │ uvicorn main:app (runtime)
           │ Loads both files into memory
           ▼
┌─────────────────────┐
│ FastAPI Server      │  Serves API requests
│ (Running process)   │  Computes search similarity
└─────────────────────┘
```

### Why Pre-compute?

We run `extract.py` and `embed.py` once locally, then commit the results:

**Cost**:
- Extraction: ~$2 in Claude API calls
- Embedding: ~$0.18 in Voyage API calls
- Running on every request? $2+ per user session!

**Speed**:
- Extraction: 30+ minutes (API rate limits)
- Embedding: ~1 minute
- Loading from JSON: <1 second

**Reliability**:
- API calls can fail, rate limit, timeout
- JSON files just work

---

## Frontend-Backend Communication

### The Fetch Pattern

Every page follows the same pattern:

```javascript
// 1. User triggers action (page load, button click, etc.)

// 2. Frontend sends request to backend
const response = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: "AI concerns", limit: 20 })
});

// 3. Backend processes and returns JSON
// (see main.py endpoints)

// 4. Frontend parses response
const data = await response.json();

// 5. Frontend updates the DOM
for (const result of data.results) {
    const card = document.createElement('div');
    card.innerHTML = `<h3>${result.job_title}</h3>`;
    container.appendChild(card);
}
```

### API Design: REST Conventions

Our endpoints follow REST patterns:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/transcripts` | GET | List resources (with filters) |
| `/api/transcript/{id}` | GET | Get single resource by ID |
| `/api/search` | POST | Complex query (body too big for URL) |
| `/api/summary` | GET | Aggregated data |

**Why POST for search?**
- GET requests put parameters in the URL
- URLs have length limits (~2000 chars)
- Search queries + filters could exceed this
- POST puts data in the request body (no limit)

### JSON: The Universal Format

All data exchange uses JSON because:
- JavaScript parses it natively (`response.json()`)
- Python handles it easily (`json.loads()`)
- Human-readable for debugging
- Industry standard for web APIs

---

## Semantic Search Implementation

This is the most technically interesting part. Let's break it down:

### What Are Embeddings?

Embeddings convert text into numbers that capture meaning:

```
"I love AI tools"     → [0.2, -0.5, 0.8, 0.1, ...]  (1024 numbers)
"AI assistants rock"  → [0.3, -0.4, 0.7, 0.2, ...]  (similar numbers!)
"I hate Mondays"      → [-0.6, 0.2, -0.3, 0.9, ...] (different numbers)
```

Similar meanings = similar numbers = similar positions in 1024-dimensional space.

### The Search Flow

```
User types: "worried about job loss"
                    │
                    ▼
┌─────────────────────────────────────┐
│ Voyage AI API                       │
│ Converts query to 1024-dim vector   │
│ [0.1, -0.3, 0.7, ...]              │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│ main.py: cosine_similarity()        │
│ Compare query vector to all 1,250   │
│ transcript vectors                  │
│                                     │
│ transcript_042: 0.85 similarity     │
│ transcript_891: 0.79 similarity     │
│ transcript_003: 0.31 similarity     │
└─────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────┐
│ Sort by similarity, return top 20   │
└─────────────────────────────────────┘
```

### Cosine Similarity Explained

```python
def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(x * x for x in b) ** 0.5
    return dot_product / (magnitude_a * magnitude_b)
```

Think of it as: "What angle are these two arrows pointing?"
- Same direction (similar meaning): cosine = 1.0
- Perpendicular (unrelated): cosine = 0.0
- Opposite (opposite meaning): cosine = -1.0

### Why Voyage AI?

We chose Voyage AI because:
1. Anthropic recommends them for embeddings
2. Good balance of quality and cost
3. Simple API (similar to OpenAI's)
4. `voyage-3` model designed for retrieval tasks

Alternatives: OpenAI embeddings, Cohere, local models (slower but free)

---

## Key Design Decisions

### 1. In-Memory Data Storage

**Choice**: Load JSON into Python dicts at startup
**Alternative**: Use a database (PostgreSQL, SQLite)

**Why we chose this**:
- Dataset is small (1,250 items, ~15MB)
- Read-only data (no user writes)
- Simpler deployment (no database to manage)
- Faster queries (no network/disk latency)

**When to use a database**:
- Data changes frequently
- Multiple servers need shared state
- Data too large for memory
- Need complex queries (JOINs, aggregations)

### 2. Vanilla JavaScript (No React/Vue)

**Choice**: Plain HTML + CSS + JavaScript
**Alternative**: React, Vue, Svelte, etc.

**Why we chose this**:
- Pages are relatively simple
- No complex state management needed
- No build step = simpler deployment
- Easier to understand for learning

**When to use a framework**:
- Complex UI with many interactive components
- Shared state across components
- Team already knows React/Vue
- Need component libraries (Material UI, etc.)

### 3. Pre-computed Embeddings

**Choice**: Generate embeddings once, store in JSON
**Alternative**: Compute embeddings on-demand

**Why we chose this**:
- Embeddings don't change (transcripts are static)
- Saves API costs ($0.18 once vs. per-request)
- Faster searches (no API call for documents)
- Works offline (only queries need API)

**When to compute on-demand**:
- Data changes frequently
- Too much data to store all embeddings
- Need to embed user-uploaded content

### 4. Synchronous Search (No Background Jobs)

**Choice**: Search completes in single request
**Alternative**: Queue job, poll for results

**Why we chose this**:
- Search is fast enough (<500ms)
- Simpler user experience
- No job queue infrastructure needed

**When to use background jobs**:
- Operations take >30 seconds
- Need to process large batches
- Want to show progress updates

---

## What We Didn't Do (And Why)

Understanding what we skipped helps clarify the architecture:

### No Authentication

We didn't add login because:
- Data is public (Anthropic released it)
- No user-specific features
- Simpler deployment

If we added it: JWT tokens, session cookies, user database

### No Caching Layer

We didn't add Redis/Memcached because:
- Data is already in memory
- No expensive computations to cache
- Single server (no shared cache needed)

If we added it: Cache search results, reduce Voyage API calls

### No Database

We didn't add PostgreSQL/MongoDB because:
- Data is static (read-only)
- Small enough for memory
- JSON files are simpler

If we added it: Better for dynamic data, complex queries, multiple servers

### No Containerization

We didn't use Docker because:
- Render handles deployment
- Single simple service
- No complex dependencies

If we added it: Reproducible builds, local/prod parity, easier scaling

---

## Ideas for Further Learning

### Beginner Projects

1. **Add a "favorites" feature**
   - Store favorites in browser localStorage
   - Learn: Client-side storage, state management

2. **Add dark mode**
   - CSS custom properties (variables)
   - Learn: CSS theming, user preferences

3. **Export search results to CSV**
   - Generate file in JavaScript
   - Learn: Blob API, file downloads

### Intermediate Projects

4. **Add user authentication**
   - Let users save searches and notes
   - Learn: JWT, sessions, password hashing
   - Tools: FastAPI-Users, Auth0

5. **Replace JSON with SQLite**
   - Use a real database
   - Learn: SQL, ORMs (SQLAlchemy)
   - Benefit: Practice database skills

6. **Add a React frontend**
   - Rebuild one page in React
   - Learn: Components, hooks, state
   - Compare: Complexity vs. vanilla JS

7. **Implement caching**
   - Cache Voyage API responses
   - Learn: Redis, cache invalidation
   - Benefit: Reduce API costs

### Advanced Projects

8. **Add real-time collaborative annotations**
   - Multiple users annotate transcripts
   - Learn: WebSockets, conflict resolution
   - Tools: Socket.io, Pusher

9. **Build a RAG chatbot**
   - Chat with the interview data
   - Learn: Retrieval-Augmented Generation
   - Use semantic search to find context, feed to LLM

10. **Deploy with Kubernetes**
    - Containerize and orchestrate
    - Learn: Docker, K8s, scaling
    - Overkill for this app, but great learning

11. **Add observability**
    - Logging, metrics, tracing
    - Learn: Structured logging, Prometheus
    - See how production apps monitor health

### Questions to Explore

- What happens if we get 10,000 transcripts? 100,000?
- How would we handle multiple users writing data?
- What if Voyage AI goes down during a search?
- How would we A/B test different search algorithms?
- What would change if this needed to run on mobile?

---

## Recommended Resources

### Web Development Fundamentals
- [MDN Web Docs](https://developer.mozilla.org/) - The definitive reference
- [javascript.info](https://javascript.info/) - Modern JS tutorial
- [CSS-Tricks](https://css-tricks.com/) - CSS deep dives

### Python Web Development
- [FastAPI Tutorial](https://fastapi.tiangolo.com/tutorial/) - Official docs are excellent
- [Real Python](https://realpython.com/) - Python tutorials

### AI/ML for Developers
- [Embeddings explained](https://platform.openai.com/docs/guides/embeddings) - OpenAI's guide
- [RAG tutorial](https://docs.anthropic.com/en/docs/build-with-claude/retrieval-augmented-generation) - Anthropic's guide

### System Design
- [System Design Primer](https://github.com/donnemartin/system-design-primer) - Free resource
- [Designing Data-Intensive Applications](https://dataintensive.net/) - The book on this topic

---

## Summary

This application is intentionally simple, but that simplicity is a feature, not a limitation. By avoiding unnecessary complexity, we:

1. **Ship faster**: No build steps, no database setup, no container orchestration
2. **Debug easier**: Fewer moving parts means fewer places for bugs to hide
3. **Learn clearer**: Each piece has one job, making the architecture transparent

As you manage AI coding assistants, remember: **the best architecture is the simplest one that solves the problem**. Start simple, add complexity only when you have a specific reason.

When an AI suggests adding React, a database, Redis, Docker, and Kubernetes to a 1,250-item read-only dataset... that's a sign to push back and ask "why?"
