# 🚀 OrqFlow 15-Day Chronological Git Commit Roadmap

This roadmap breaks down the OrqFlow codebase into clean, daily incremental commits. It builds the GitHub repository history logically from the bottom up—starting with configuration and database schemas, advancing through the multi-agent LangGraph orchestration engine, constructing the React frontend, and concluding with regression testing and CI/CD.

> **Note:** Per project rules, internal prompts (`app/graph/prompts.py`), general documentation files (`*.md`), environment secrets (`.env`), and temporary scratch scripts are explicitly excluded.

---

## 🚫 Files & Folders to Exclude (`.gitignore`)
Ensure these items are ignored before starting Day 1:
* `app/graph/prompts.py` *(Internal LLM system prompts)*
* `*.md` & `docs/` *(Documentation files)*
* `.env`, `.env.*` *(API keys and database credentials)*
* `.gemini/`, `scratch/`, `__pycache__/`, `node_modules/`, `dist/`

---


## 🗓️ 15-Day GitHub Push Schedule

### Phase 1: Foundation & Database Architecture

#### Day 1: Project Skeleton & Configuration
* **Files:** `.gitignore`, `requirements.txt`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `app/config.py`, `app/__init__.py`
* **Commit Message:**
  ```text
  chore: initialize project configuration, Docker topology, and environment settings
  ```

#### Day 2: SQLAlchemy ORM Models & Alembic Setup
* **Files:** `app/models.py`, `app/database.py`, `app/errors.py`, `alembic.ini`, `alembic/env.py`
* **Commit Message:**
  ```text
  feat(db): implement async SQLAlchemy models and database migration engine
  ```

#### Day 3: Database Migration Scripts & Seed Data
* **Files:** `alembic/versions/001_initial_schema.py`, `alembic/versions/002_company_ops_schema.py`
* **Commit Message:**
  ```text
  feat(db): add schema migrations for agent memory and company operations data
  ```

---

### Phase 2: Backend API & Model Context Protocol (MCP)

#### Day 4: FastAPI Core App & Security Middleware
* **Files:** `app/main.py`, `app/dependencies.py`, `app/auth.py`, `app/routers/health.py`, `app/routers/__init__.py`, `app/middleware/rate_limit.py`, `app/middleware/request_id.py`, `app/middleware/__init__.py`
* **Commit Message:**
  ```text
  feat(api): build FastAPI application lifecycle, health endpoints, JWT auth, and Redis rate-limiting
  ```

#### Day 5: FastMCP Specialist Servers
* **Files:** `mcp_servers/db_server.py`, `mcp_servers/files_server.py`, `mcp_servers/search_server.py`, `mcp_servers/shared_auth.py`, `mcp_servers/__init__.py`
* **Commit Message:**
  ```text
  feat(mcp): implement FastMCP tool servers for SQL query, filesystem, and web search
  ```

---

### Phase 3: LangGraph Multi-Agent Orchestration

#### Day 6: Agent State & Tool Bindings
* **Files:** `app/graph/state.py`, `app/graph/tools.py`, `app/graph/memory.py`, `app/graph/__init__.py`
* **Commit Message:**
  ```text
  feat(graph): define multi-agent state definitions and dynamic MCP tool loaders
  ```

#### Day 7: Automatic LLM Fallback Engine
* **Files:** `app/graph/fallback.py`
* **Commit Message:**
  ```text
  feat(graph): build 4-tier automatic failover chain switching between Groq and Gemini models
  ```

#### Day 8: Supervisor & Specialist Nodes
* **Files:** `app/graph/nodes.py`
* **Commit Message:**
  ```text
  feat(graph): implement supervisor routing logic and ReAct specialist worker nodes
  ```

#### Day 9: StateGraph Builder & Compiler
* **Files:** `app/graph/builder.py`
* **Commit Message:**
  ```text
  feat(graph): construct LangGraph topology and state checkpointer integration
  ```

---

### Phase 4: API Routers & Observability

#### Day 10: SSE Streaming Router & Step Recorder
* **Files:** `app/routers/agent_router.py`, `app/recorder.py`
* **Commit Message:**
  ```text
  feat(api): implement Server-Sent Events real-time stream and step execution logger
  ```

#### Day 11: Authentication & Thread Endpoints
* **Files:** `app/routers/auth_router.py`
* **Commit Message:**
  ```text
  feat(api): add endpoints for user authentication and chat session thread management
  ```

---

### Phase 5: React Studio Frontend

#### Day 12: Frontend Foundation & Design Tokens
* **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`, `frontend/index.html`, `frontend/public/`, `frontend/src/main.tsx`, `frontend/src/index.css`, `frontend/src/App.css`, `frontend/src/assets/`
* **Commit Message:**
  ```text
  feat(ui): initialize React Vite workspace with Tailwind styling tokens and asset dependencies
  ```

#### Day 13: Topology & Observability Visualizers
* **Files:** `frontend/src/components/TopologyBar.tsx`, `frontend/src/components/TraceInspector.tsx`
* **Commit Message:**
  ```text
  feat(ui): build interactive agent graph topology bar and step run trace modal
  ```

#### Day 14: Studio Arena & SSE Client
* **Files:** `frontend/src/App.tsx`
* **Commit Message:**
  ```text
  feat(ui): implement multi-agent chat arena with rich Markdown rendering and SSE stream consumer
  ```

---

### Phase 6: Quality Assurance & CI/CD

#### Day 15: Automated Test Suite, Production Overlay & Continuous Integration
* **Files:** `README.md`, `docs/deployment.md`, `docker-compose.prod.yml`, `.dockerignore`, `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_agent.py`, `tests/test_auth.py`, `tests/test_graph.py`, `tests/test_health.py`, `tests/test_mcp_auth.py`, `tests/test_mcp_db.py`, `tests/test_mcp_files.py`, `tests/test_mcp_search.py`, `.github/workflows/keep-alive.yml`, `scripts/test_login.py`, `scripts/create_test_user.py`, `scripts/run_routing_eval.py`
* **Commit Message:**
  ```text
  test: add comprehensive 95-test regression suite, production Docker overlay, deployment docs, and CI workflows
  ```

---

## 💡 Daily Terminal Execution Guide
When pushing daily, run the following commands in your workspace root:

```powershell
# Example for Day 1
git add .gitignore requirements.txt pyproject.toml docker-compose.yml app/config.py app/exceptions.py
git commit -m "chore: initialize project configuration, Docker topology, and environment settings"
git push origin main
```
