# ✈️ AI Travel Agent

A multi-agent travel assistant built with **Deep Agents**, **MCP**, **RAG**, and a **FastAPI** chat UI.  
It plans trips in natural language, searches flights and hotels, suggests destinations from a knowledge base, and creates real bookings — with human approval for sensitive actions.

---

## ✨ Features

| | Area | What you get |
|---|------|----------------|
| 🧠 | **Deep Agent orchestrator** | Plans multi-step trips, asks only for missing params, remembers the thread |
| 🤖 | **Specialist subagents** | Flight, hotel, destination (RAG), itinerary, booking — each with its own tools & skills |
| 🔌 | **MCP tool layer** | Flights, hotels, bookings, and knowledge search exposed via a FastMCP server |
| 🎫 | **Real bookings** | `create` / `cancel` / `get` / `list` persist in SQLite (not just chat suggestions) |
| ✋ | **HITL approval** | `create_booking` and `cancel_booking` pause until approve / reject |
| 📚 | **RAG knowledge base** | BM25 over Persian-first city guides (attractions, neighborhoods, transport, tips) |
| 🛠️ | **Skills** | Trip planning, flight/hotel search, destination guide, itinerary, booking management |
| 💬 | **Chat UI + API** | Browser chat with thread history, live streaming status, and approval controls |
| 📡 | **SSE streaming** | Live subagent status + token streaming (`/v1/*/stream`) |
| 🗂️ | **Mock catalog** | 200 flights + 200 hotels across many cities and dates |

---

## 🏗️ Architecture (short)

```
👤 User (Chat UI / CLI)
        │
        ▼
🌐 FastAPI / session
        │
        ▼
🧭 Travel Orchestrator (Deep Agent)
   ├─ ✈️  flight-agent      → search_flights
   ├─ 🏨  hotel-agent       → search_hotels
   ├─ 🗺️  destination-agent → search_knowledge (RAG)
   ├─ 📅  itinerary-agent   → search_knowledge (RAG)
   └─ 🧾  booking-agent     → create/cancel/get/list  (+ ✋ HITL)
        │
        ▼
🔌 MCP Server  →  🗄️ SQLite backend + 📚 BM25 index
```

> 💡 **RAG is tool-mediated**, not automatic context stuffing: the orchestrator decides when to delegate to destination/itinerary agents; those call `search_knowledge`.

---

## 🚀 Quick start

### 1️⃣ Setup

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # then edit keys
```

### 2️⃣ Configure `.env`

```env
LLM_API_KEY=your_key
LLM_BASE_URL=https://your-gateway   # optional
TRAVEL_AGENT_MODEL=openai/gpt-4o
```

### 3️⃣ Build the RAG index (first time / after knowledge changes)

```bash
python -m rag build
```

### 4️⃣ Run the API + chat UI

```bash
python -m api
```

Open **http://127.0.0.1:8000** 🌐 (Swagger: `/docs` 📖).

### 5️⃣ Optional CLI

```bash
python -m agent
```

---

## 📡 API overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/chat` | 💬 Send a message |
| `POST` | `/v1/chat/stream` | 📡 Same + SSE status/tokens |
| `POST` | `/v1/approve` / `/v1/approve/stream` | ✅ Approve pending booking action |
| `POST` | `/v1/reject` / `/v1/reject/stream` | ❌ Reject pending action |
| `GET` | `/v1/threads` | 🧵 List chat threads |
| `GET` | `/v1/threads/{id}` | 📜 History + pending |
| `GET` | `/health` | 💚 Liveness |

Keep the same `thread_id` to continue a conversation and complete HITL.

---

## 🤖 Subagents & skills

| | Subagent | Role | Skill |
|---|----------|------|--------|
| ✈️ | `flight-agent` | Search & compare flights | `flight-search` |
| 🏨 | `hotel-agent` | Search & compare hotels | `hotel-search` |
| 🗺️ | `destination-agent` | City tips via RAG | `destination-guide` |
| 📅 | `itinerary-agent` | Day-by-day plan via RAG | `itinerary-builder` |
| 🧾 | `booking-agent` | Create / cancel / status | `booking-management` |
| 🧭 | Orchestrator | Multi-step trip planning | `trip-planning` |

---

## 🌍 Knowledge cities (RAG)

Guides under `rag/knowledge/` (overview, attractions, neighborhoods, transport, culture tips):

🇳🇱 Amsterdam · 🇹🇷 Ankara · 🇦🇿 Baku · 🇹🇭 Bangkok · 🇪🇸 Barcelona · 🇩🇪 Berlin · 🇪🇬 Cairo · 🇶🇦 Doha · 🇦🇪 Dubai · 🇩🇪 Frankfurt · 🇹🇷 Istanbul · 🇲🇾 Kuala Lumpur · 🇬🇧 London · 🇪🇸 Madrid · 🇷🇺 Moscow · 🇫🇷 Paris · 🇨🇿 Prague · 🇮🇹 Rome · 🇬🇪 Tbilisi · 🇯🇵 Tokyo · 🇦🇹 Vienna

```bash
python -m rag search "جاذبه‌ها" --city istanbul
```

---

## 📁 Project layout

```
agent/           # 🧭 Orchestrator, session/HITL, subagents, MCP client
api/             # 🌐 FastAPI + static chat UI
backend/         # 🗄️ SQLite catalog + booking services
mcp_server/      # 🔌 FastMCP tools (flights, hotels, bookings, knowledge)
rag/             # 📚 BM25 retriever + Persian knowledge markdown
skills/          # 🛠️ Deep Agent skills per specialist
data/            # 💾 Local DB & checkpoints (gitignored)
```

---

## 💡 Example prompts

- ✈️ Find flights Tehran → Istanbul on 2026-11-10 and compare two options  
- 🏨 Hotels in Dubai under $150 / night for 3 nights  
- 🗺️ Attractions and neighborhoods in Tbilisi  
- 📅 Build a 3-day itinerary for Barcelona  
- 🧾 Book flight `FL001` for Ali (will pause for your approval)

---

## 🧩 Design notes

- 📝 **Prompt vs Skill** — stable rules live in the orchestrator system prompt; long workflows live in skills and load when needed.  
- 🔌 **MCP vs agents** — MCP owns executable tools; agents decide *when* to call them.  
- ✋ **HITL** — booking create/cancel interrupts are scoped by `thread_id`; approve/reject is idempotent if nothing is pending.

---

## 📄 License

Use freely for learning and demos. Add a license file if you publish a commercial fork.

---

<p align="center">Made for smarter trip planning ✈️🌍</p>
