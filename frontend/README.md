# OrqFlow Studio Frontend Client

This directory contains the production-ready React + Vite + Tailwind CSS web interface for interacting with the OrqFlow Multi-Agent Orchestration API.

## Core Features Implemented

1. **POST + Server-Sent Events (SSE) Streaming:** Uses `@microsoft/fetch-event-source` to maintain persistent connection with `POST /api/threads/{id}/run`, displaying live text tokens, specialist node transitions (`node_start`), and active routing decisions.
2. **Glassmorphism Design Aesthetic:** Built using design variables defined in `docs/design-system.md` featuring obsidian backgrounds (`#0A0A0C`), elevated dark surfaces (`#141418`), and specialist accent glows (Purple for Supervisor, Blue for Researcher, Emerald for Analyst, Amber for Coder, Pink for Responder).
3. **Live Topology Bar:** Displays active node states with micro-animations (`animate-pulse`, spinners) indicating real-time agent processing.
4. **Interactive Trace Inspector:** Toggleable right-hand drawer fetching SQL audit entries from `GET /api/runs/{id}/trace`, showcasing step latency metrics (`latency_ms`) and tool call arguments.
5. **Session Management & Auto-Login:** Quick test authentication banner for rapid testing against backend thread persistence APIs (`POST /api/threads`).

## Getting Started

### Installation
```bash
cd frontend
npm install
```

### Development Server
Run locally with automatic Vite proxying to `http://localhost:8000`:
```bash
npm run dev
```
The studio will be accessible at `http://localhost:5173`.

### Production Build
Compile TypeScript and bundle assets:
```bash
npm run build
```
Compiled output is saved inside `frontend/dist/`.
