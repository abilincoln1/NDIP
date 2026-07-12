# RTIFN Agora Observatory — Setup Guide

## What is this?

A modular civic engagement and social intelligence platform for the RTIFN diaspora network.  
It aggregates opt-in participation data and public discourse signals (via official APIs only) into a clean analytics dashboard.

---

## Quick start (Docker — recommended)

### Prerequisites
- Docker Desktop installed
- 4 GB RAM free

### 1. Clone / download the project

```bash
# If from git:
git clone <your-repo-url>
cd agora
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` — the minimum required:

```env
SECRET_KEY=change-me-to-a-random-32-char-string
DATABASE_URL=postgresql://agora_user:agora_pass@db:5432/agora_db
```

Social API keys are **optional** — the platform works without them. Add any you have:

```env
YOUTUBE_API_KEY=          # https://console.cloud.google.com
TWITTER_BEARER_TOKEN=     # https://developer.twitter.com
REDDIT_CLIENT_ID=         # https://www.reddit.com/prefs/apps
REDDIT_CLIENT_SECRET=
NEWS_API_KEY=             # https://newsapi.org
```

> **GDELT** is always available — no key needed.  
> **Reddit** works without credentials (rate-limited) and better with them.

### 3. Start all services

```bash
docker compose up --build
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379  
- FastAPI backend on port 8000  
- Next.js frontend on port 3000

### 4. Seed with sample data (optional but recommended)

In a second terminal:

```bash
docker compose exec backend python scripts/seed.py
```

### 5. Open the dashboard

- **Dashboard**: http://localhost:3000
- **API docs**: http://localhost:8000/docs
- **Login**: `admin@agora.rtifn.org` / `AgoraAdmin2024!`

---

## Manual setup (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m textblob.download_corpora lite

cp .env.example .env
# edit .env with your DATABASE_URL pointing to your local PostgreSQL

# Create database
createdb agora_db  # or use pgAdmin

# Run migrations / create tables
uvicorn app.main:app --reload
# Tables auto-created on first startup via SQLAlchemy

# Seed data
python scripts/seed.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Replit deployment

1. Create a new Replit from the project folder.
2. Add Secrets in Replit dashboard for each `.env` variable.
3. Set the run command:
   ```
   cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
4. For the frontend, create a second Replit or use Vercel free tier.
5. Point `NEXT_PUBLIC_API_URL` to your backend Replit URL.

---

## API keys — where to get them

| Platform | URL | Notes |
|----------|-----|-------|
| YouTube | https://console.cloud.google.com → APIs → YouTube Data API v3 | Free tier: 10,000 units/day |
| X/Twitter | https://developer.twitter.com | Requires paid Basic tier ($100/mo) for search |
| Reddit | https://www.reddit.com/prefs/apps | Free, create "script" app |
| NewsAPI | https://newsapi.org | Free tier: 100 requests/day |
| GDELT | No key needed | Always available |

---

## Ethical constraints enforced in code

- Emails are SHA-256 hashed before storage — never stored in plain text
- No author IDs stored from social APIs — only post content + metadata
- All analytics are aggregated counts — no individual-level analysis
- Social listening only uses official read-only API endpoints
- No scraping, no rate-limit bypassing, no private data reconstruction
- Reports are generated with neutral factual tone markers

---

## Project structure

```
agora/
├── backend/
│   ├── app/
│   │   ├── api/routes/       ← FastAPI route handlers
│   │   ├── analytics/        ← Metrics engine + NLP
│   │   ├── connectors/       ← Social API connectors
│   │   ├── core/             ← Config + security
│   │   ├── db/               ← Database session
│   │   ├── models/           ← SQLAlchemy models
│   │   ├── schemas/          ← Pydantic schemas
│   │   └── services/         ← Report generation
│   ├── alembic/              ← DB migrations
│   ├── scripts/seed.py       ← Dev data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/              ← Next.js pages
│       ├── components/       ← UI + charts
│       └── lib/api.ts        ← API client
└── docker-compose.yml
```

---

## Adding a new social connector

1. Create `backend/app/connectors/myplatform.py`
2. Extend `BaseConnector` and implement `fetch()`
3. Add to `ALL_CONNECTORS` list in `registry.py`
4. Add any API key to `config.py` + `.env.example`

The connector will automatically appear in the dashboard status panel and be available for ingest jobs.

---

## Generating analytics snapshots

Snapshots power the trend charts. Run manually or add to a cron:

```bash
curl -X POST http://localhost:8000/analytics/snapshot \
  -H "Authorization: Bearer <your-token>"
```

Or add APScheduler to `main.py` to run this automatically every 24 hours.
