# 🤖 The Master AI Interview Curriculum Generator Prompt
**Copy & Paste this prompt into any AI Coding Assistant (Antigravity, Cursor, Claude Code, GitHub Copilot, ChatGPT) inside any project workspace to instantly generate a 5–6 Hour Complete Mastery & 15-Minute Crisp Pre-Interview Curriculum!**

---

## 📋 How to Use This Prompt
1. Open your terminal or AI IDE chat inside **any software repository** (monolith, microservices, fullstack SPA, backend API, mobile app, or data engineering pipeline).
2. Copy the entire prompt block between the `<MASTER_PROMPT>` and `</MASTER_PROMPT>` tags below.
3. Paste it directly into the AI chat box and submit.
4. Watch the AI thoroughly analyze your codebase and generate your customized `interview_prep/` library!

---

```markdown
<MASTER_PROMPT>
You are a Senior Principal Systems Architect and Principal Technical Interviewer at a top-tier tech company. 

I built this software repository by following tutorials, documentation, and experimenting with code ("vibe coded" it). While I understand how individual files and technologies work in isolation, I need you to teach me the system from a high-level architectural perspective down to granular engineering mechanics so I can ace senior-level technical interviews.

### 🛑 STEP 1: Deep Codebase & Architectural Analysis
Before creating any documents, thoroughly inspect and analyze this entire repository:
1. Examine package dependencies (`package.json`, `requirements.txt`, `pom.xml`, `go.mod`, `Cargo.toml`, `docker-compose.yml`, `.env` templates).
2. Identify all services, modules, database engines, ORMs/query builders, message brokers/queues, authentication protocols, and caching layers.
3. Map the exact data flow: Trace how a client request enters the system, traverses middleware/gateways, executes database transactions/locks, emits background events, and returns a response.
4. Identify the #1 most technically challenging problem solved in this codebase (e.g., concurrency, race conditions, distributed transactions, idempotency, rate-limiting, complex SQL JOINs, or real-time websocket synchronization).

---

### 🛑 STEP 2: Create the Modular `interview_prep/` Curriculum
Create a dedicated folder named `interview_prep/` inside the workspace root and write exactly **5 highly detailed, production-grade Markdown handbooks** (`00_` to `03_` plus an index file). 

Do not summarize or skip sections—write complete, comprehensive, textbook-quality documentation filled with real code snippets from this repository, exact SQL/Schema definitions, ASCII architecture diagrams, physical analogies, and ready-to-speak interview scripts.

#### 📄 File 1: `interview_prep/00_15_MIN_CRISP_PRE_INTERVIEW_CHEAT_SHEET.md`
*(Target: A high-density, super-crisp review document designed to be read in 15–20 minutes right before stepping into the interview.)*
Must include:
1. **🚀 The 60-Second Golden Intro**: Exactly what to say word-for-word when the interviewer asks, *"Tell me about a complex technical project you built."* (Pack this with high-impact, accurate engineering buzzwords backed by the true architecture).
2. **🏛️ Architectural Glance Box**: A crisp table mapping every service/module, its port/folder, core tech stack, and primary engineering responsibility.
3. **🔥 The 4 Hardest Technical Concepts Explained Simply**: Explain the 4 most complex mechanics in this project (e.g., ACID locking, idempotency, asynchronous queues, reverse proxying, or caching algorithms) in plain English so I can explain them effortlessly under pressure.
4. **⚔️ Rapid-Fire Attack & Defense (Top 6 Grilling Questions)**: Provide bulletproof, conversational answers to the 6 hardest follow-up questions an interviewer will ask (e.g., *"Why did you choose this database over NoSQL/SQL?"*, *"What happens if this specific service/node crashes mid-transaction?"*, *"Where is state managed across the system?"*, *"Why didn't you use X alternative?"*).
5. **🧠 Buzzword Power Dictionary**: A checklist of 8–10 precision engineering terms specific to this project to drop naturally during the conversation.

---

#### 📄 File 2: `interview_prep/README_INTERVIEW_SYLLABUS.md`
*(Target: Master Executive Index & 5–6 Hour Study Syllabus connecting all study handbooks.)*
Must include:
1. Executive summary of the curriculum and learning outcomes.
2. Complete directory tree overview linking to all files inside `interview_prep/`.
3. Clear summaries of what each handbook covers and how they fit together.
4. A quick-start navigation guide for structured morning/afternoon study sessions.

---

#### 📄 File 3: `interview_prep/01_MASTER_INTERVIEW_PREP_GUIDE.md`
*(Target: A comprehensive 2-hour Socratic study guide answering the core 10 interview preparation requirements.)*
Must include:
1. **Project Overview**: Problem solved, what we built, target users, and core features.
2. **Architecture & Mental Picture**: Why each technology was chosen, exact service connectivity, and a comprehensive **ASCII Architecture Diagram**.
3. **End-to-End Flow**: Step-by-step trace of the primary user transaction from UI click to database commit and asynchronous background worker processing.
4. **Component Breakdown**: Module/service interaction matrix (upstream callers vs. downstream targets and data payloads).
5. **Natural Walkthrough Scripts**:
   - A conversational **3–5 Minute Walkthrough Script** answering *"Walk me through your project."*
   - A punchy **1-Minute Elevator Pitch**.
6. **Deep Dive Questions & Answers**: Comprehensive follow-up Q&A covering tech stack rationale, auth flows, state management, security layers, and error handling.
7. **The Most Challenging Part**: Deep dive into the #1 technical challenge in this codebase. Explain *why* it was difficult, *how* it was solved (with code snippets), and give a realistic interview narrative.
8. **Unique & Resume-Worthy Highlights**: How to frame this project to stand out from generic CRUD applications using senior engineering terminology.
9. **Potential Future Improvements**: High-impact architectural roadmap (e.g., Kubernetes K8s auto-scaling, Redis caching, Circuit Breakers, Event-Driven Sagas, or GraphQL federation).
10. **Socratic Teaching & Analogies**: Create a vivid, real-world physical analogy (like an Airport Terminal, Bank Vault, Restaurant Kitchen, or Post Office) explaining *why* every major component exists so I never have to memorize scripts.

---

#### 📄 File 4: `interview_prep/02_THE_FINAL_ONE_STOP_HANDBOOK.md`
*(Target: A comprehensive 2-hour technical reference and study itinerary.)*
Must include:
1. **Complete Route-by-Route & API Reference**: Exhaustive table of every HTTP/Websocket/RPC endpoint, required authentication headers, request parameters/payloads, and exact downstream database/service behavior across the entire repository.
2. **Exact Database Table & Data Schemas**: Full `CREATE TABLE`, ORM schema, or document model definitions including primary keys, foreign keys, indexes, and constraints for every entity in the codebase.
3. **In-Depth Architectural Concepts Explained**: Textbook-level explanations of the core theoretical protocols used here (e.g., `SELECT ... FOR UPDATE` index record locks, JWT RS256/HS256 signature verification, AMQP `channel.ack`/`channel.nack` message durability, or OAuth2/PKCE handshakes).
4. **1-Day Hour-by-Hour Study & Mastery Schedule**: A realistic 6-hour intensive study itinerary for the day before the interview.
5. **Rapid Revision Flashcards**: 10–12 high-speed Q&A flashcards for quick review on the morning of the interview.

---

#### 📄 File 5: `interview_prep/03_DEEP_DIVE_ENGINEERING_MECHANICS.md`
*(Target: A granular 1.5-hour engineering deep dive inspecting the hardest code execution paths.)*
Must include:
1. **Security & Middleware Pipeline**: Line-by-line code walkthrough of how rate-limiting, authentication middleware, reverse proxying, or CORS policies are initialized and executed.
2. **Concurrency, Transaction & Locking Mechanics**: Step-by-step code and database execution trace showing exactly how atomic transactions, locking mechanisms, or state synchronized checks prevent race conditions under peak concurrent load.
3. **Resilience, Retries & Idempotency**: Code walkthrough explaining how the system handles network dropouts, API timeouts, idempotency key validation, or duplicate request suppression.
4. **Asynchronous & Background Worker Pipelines**: Complete walkthrough of any message broker queues, cron jobs, webhooks, or background worker loops, explaining what happens if a node crashes mid-task and how negative acknowledgments or dead-letter queues (`DLQ`) guarantee zero data loss.

---

### 🛑 STEP 3: Execution Rules
- Write all 5 files directly to the filesystem inside the `interview_prep/` folder using your file writing tools.
- Never use placeholder text like `/* code goes here */` or `... similar for other routes ...`. Provide 100% complete, real code snippets and schema statements from the analyzed codebase.
- Ensure all markdown tables, ASCII diagrams, and code blocks are perfectly formatted and readable.
- Once finished, output a clean confirmation summarizing the generated library and directing me to start with `00_15_MIN_CRISP_PRE_INTERVIEW_CHEAT_SHEET.md`.
</MASTER_PROMPT>
```
