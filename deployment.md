# 🚀 OrqFlow — Free-Tier Cloud Deployment Guide

> **Every service is hosted 100% for free.** No credit card required for initial deployment.

---

## Architecture Overview

```
User Browser
    │
    ▼
[Vercel] — React + Vite (SPA)          FREE · unlimited bandwidth
    │  (VITE_API_BASE_URL)
    ▼
[Render] — FastAPI API (api service)   FREE · 750 hrs/month
    │  (DATABASE_URL, REDIS_URL, MCP_*_URL, LLM keys)
    ├──→ [Render] MCP DB Server     (port 8001)  FREE
    ├──→ [Render] MCP Search Server (port 8002)  FREE
    └──→ [Render] MCP Files Server  (port 8003)  FREE
    │
    ├──→ [Neon]    PostgreSQL        FREE · 512MB storage
    ├──→ [Upstash] Redis             FREE · 10k cmds/day
    └──→ [Groq]    LLM Inference     FREE · 14,400 tokens/min
```

---

## Services You Need (All Free)

| Service | Purpose | Free Limit | Sign-Up |
|---------|---------|-----------|---------|
| **Render** | Host FastAPI + 3 MCP servers (Docker) | 750 hrs/month, sleeps after 15min | render.com |
| **Vercel** | Host React/Vite frontend (SPA) | Unlimited | vercel.com |
| **Neon** | PostgreSQL database | 512 MB, 1 DB | neon.tech |
| **Upstash** | Redis (rate-limiter + checkpointer) | 10,000 cmds/day | upstash.com |
| **Groq** | LLM inference (Llama 3.3 70B) | 14,400 tokens/min | console.groq.com |
| **Tavily** | Web search API | 1,000 searches/month | tavily.com |

---

## Step 1 — Neon PostgreSQL (Free Database)

1. Go to **neon.tech** → Create Project → pick a region close to your Render region.
2. Copy the **Connection String**. It looks like:
   ```
   postgresql://user:pass@ep-xxxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
3. For OrqFlow you need **two connection strings**:
   - **`DATABASE_URL`** — main app user (read/write) → use the default connection string.
   - **`MCP_DATABASE_URL`** — read-only user for the MCP DB tool server.
     - In Neon SQL editor, run:
       ```sql
       CREATE ROLE orqflow_readonly LOGIN PASSWORD 'choose_a_strong_password';
       GRANT CONNECT ON DATABASE neondb TO orqflow_readonly;
       GRANT USAGE ON SCHEMA public TO orqflow_readonly;
       GRANT SELECT ON ALL TABLES IN SCHEMA public TO orqflow_readonly;
       ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO orqflow_readonly;
       ```
     - Your `MCP_DATABASE_URL`:
       ```
       postgresql+asyncpg://orqflow_readonly:choose_a_strong_password@ep-xxxx.us-east-2.aws.neon.tech/neondb?ssl=require
       ```

> ⚠️ **IMPORTANT:** Replace the scheme prefix in DATABASE_URL from `postgresql://` to `postgresql+asyncpg://` (asyncpg requires this). Neon's SSL is automatic — asyncpg reads `?ssl=require` from the URL.

---

## Step 2 — Upstash Redis (Free Cache + Checkpointer)

1. Go to **upstash.com** → Create Database → pick a region.
2. Copy the **Redis URL** — it starts with `rediss://` (note the double `s` = SSL).
   ```
   rediss://default:your_password@your-endpoint.upstash.io:6379
   ```
3. That's it. OrqFlow's `config.py` auto-detects `upstash.io` and enables SSL.

---

## Step 3 — API Keys

| Key | Where to get | Cost |
|-----|-------------|------|
| `GROQ_API_KEY` | console.groq.com → API Keys | Free |
| `GOOGLE_API_KEY` | aistudio.google.com → Get API key | Free (Gemini fallback) |
| `TAVILY_API_KEY` | tavily.com → API | 1,000 free searches/month |

---

## Step 4 — Deploy Backend to Render (4 Web Services)

> Render's free tier gives **1 Web Service** for free that auto-sleeps. You need 4 services.
> The **main API** is the one that matters most — the 3 MCP servers can share a single Render service if needed (see note at end).

### Create the Main API Web Service

1. Go to **render.com** → New → **Web Service**
2. Connect your GitHub repo `Akshansh0519/OrqFlow`
3. Settings:
   - **Name:** `orqflow-api`
   - **Runtime:** `Docker`
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Command:** *(leave blank — uses the entrypoint)*
4. **Environment Variables** (paste these in the Render dashboard):

```ini
# ── Identity ──────────────────────────────────────────────────────────────────
ENVIRONMENT=production

# ── Database (from Neon) ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxxx.us-east-2.aws.neon.tech/neondb?ssl=require
MCP_DATABASE_URL=postgresql+asyncpg://orqflow_readonly:pass@ep-xxxx.us-east-2.aws.neon.tech/neondb?ssl=require

# ── Redis (from Upstash) ──────────────────────────────────────────────────────
REDIS_URL=rediss://default:pass@your-endpoint.upstash.io:6379

# ── JWT Secrets (generate with: python -c "import secrets; print(secrets.token_hex(32))")
ACCESS_TOKEN_SECRET=<64_char_random_hex>
REFRESH_TOKEN_SECRET=<different_64_char_random_hex>

# ── MCP Auth (shared key — same in all 4 services)
MCP_SERVER_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(32))">

# ── MCP URLs (replace with your Render service URLs after deploying MCP services)
MCP_DB_URL=https://orqflow-mcp-db.onrender.com/mcp
MCP_SEARCH_URL=https://orqflow-mcp-search.onrender.com/mcp
MCP_FILES_URL=https://orqflow-mcp-files.onrender.com/mcp

# ── CORS (set to your Vercel URL — no trailing slash!)
CLIENT_URL=https://your-orqflow-app.vercel.app

# ── Search
SEARCH_PROVIDER=tavily
TAVILY_API_KEY=tvly-your_key_here

# ── LLM Models
ROUTER_LLM_MODEL=llama-3.3-70b-versatile
WORKER_LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=gsk_your_groq_key
GOOGLE_API_KEY=AIza_your_google_key

# ── Swagger UI self-link (Render sets PORT automatically — do not set PORT here)
API_BASE_URL=https://orqflow-api.onrender.com

# ── Files Sandbox path on Render
WORKSPACE_ROOT=/opt/render/project/src/workspace
```

### Create the 3 MCP Web Services

Repeat the process 3 times with different **Start Commands**:

| Service Name | Docker Start Command |
|-------------|---------------------|
| `orqflow-mcp-db` | `python -m mcp_servers.db_server` |
| `orqflow-mcp-search` | `python -m mcp_servers.search_server` |
| `orqflow-mcp-files` | `python -m mcp_servers.files_server` |

Set the **same environment variables** on each MCP service (they all read from `app/config.py`).

> ✅ After all 4 services are deployed, go back to `orqflow-api` and update `MCP_DB_URL`, `MCP_SEARCH_URL`, `MCP_FILES_URL` with the actual Render `.onrender.com` URLs.

---

## Step 5 — Deploy Frontend to Vercel

1. Go to **vercel.com** → Add New Project → Import `Akshansh0519/OrqFlow`
2. Settings:
   - **Framework:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
3. **Environment Variable:**
   ```
   VITE_API_BASE_URL = https://orqflow-api.onrender.com
   ```
4. Deploy. Done.

---

## Step 6 — Verify Deployment (Evidence before claims)

Run these after all services are deployed:

```bash
# 1. Health check (wait up to 60s for Render cold start)
curl https://orqflow-api.onrender.com/health

# 2. Verify CORS header is present
curl -I -H "Origin: https://your-app.vercel.app" https://orqflow-api.onrender.com/health

# 3. Verify MCP DB server is alive
curl -H "Authorization: Bearer YOUR_MCP_SERVER_KEY" https://orqflow-mcp-db.onrender.com/health

# 4. Check Swagger UI loads
open https://orqflow-api.onrender.com/docs
```

Expected responses:
```json
{"status": "ok", "version": "0.1.0"}
```

---

## ⚠️ Known Free-Tier Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| **Render cold start** | First request after 15min idle takes 50–60s | Warning shown on login page |
| **Upstash 10k cmds/day** | ~3,000 API calls/day | Enough for portfolio demos |
| **Neon 512 MB storage** | Data limit | Enough for thousands of runs |
| **Groq rate limits** | 14,400 tokens/min, 30 requests/min | Built-in 4-tier fallback chain |
| **Tavily 1,000 searches/month** | Monthly search cap | Set `SEARCH_PROVIDER=mock` to disable |

---

## Generate Secrets Locally

```python
# Run this in Python to generate strong secrets:
import secrets
print("ACCESS_TOKEN_SECRET =", secrets.token_hex(32))
print("REFRESH_TOKEN_SECRET =", secrets.token_hex(32))
print("MCP_SERVER_KEY =", secrets.token_urlsafe(32))
```

---

## Local Docker Development

```bash
# Copy example env and fill in values
cp .env.example .env

# Start everything locally (Postgres + Redis included)
docker compose up --build

# Run migrations (auto-runs via docker-entrypoint.sh)
docker compose exec api alembic upgrade head

# Access
# API:      http://localhost:8000
# Docs:     http://localhost:8000/docs
# Frontend: http://localhost:5173
```
