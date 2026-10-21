"""FastAPI app — chat + HITL approve/reject for the travel orchestrator.

Run:
  .\\.venv\\Scripts\\python.exe -m api
  # or: uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent.orchestrator import create_travel_orchestrator
from agent.session import (
    TurnResult,
    approve,
    chat,
    get_pending,
    get_thread_history,
    iter_approve_events,
    iter_chat_events,
    list_threads,
)
from api.schemas import (
    ApproveRequest,
    ChatRequest,
    RejectRequest,
    ThreadHistoryResponse,
    ThreadSummary,
    TurnResponse,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"

_agent: Any | None = None
_lock = threading.Lock()


def get_agent():
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not ready")
    return _agent


def _to_response(result: TurnResult) -> TurnResponse:
    return TurnResponse(**result.to_dict())


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _agent
    _agent = create_travel_orchestrator()
    yield
    _agent = None


app = FastAPI(
    title="AI Travel Agent API",
    version="0.1.0",
    description="Chat with the Deep Agent orchestrator. Booking create/cancel pause for approval.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def chat_ui() -> FileResponse:
    """Simple browser chat UI for the travel agent API."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "ready" if _agent is not None else "loading"}


def _sse(events: Iterator[dict[str, Any]]) -> StreamingResponse:
    def generate() -> Iterator[str]:
        for event in events:
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/v1/chat", response_model=TurnResponse)
def post_chat(body: ChatRequest) -> TurnResponse:
    """Send a user message. Returns reply or needs_approval + pending tool args."""
    thread_id = body.thread_id or str(uuid.uuid4())
    agent = get_agent()
    with _lock:
        result = chat(agent, thread_id, body.message.strip())
    return _to_response(result)


@app.post("/v1/chat/stream")
def post_chat_stream(body: ChatRequest) -> StreamingResponse:
    """SSE: status + tokens + final done event for one chat turn."""
    thread_id = body.thread_id or str(uuid.uuid4())
    agent = get_agent()

    def events() -> Iterator[dict[str, Any]]:
        with _lock:
            yield from iter_chat_events(agent, thread_id, body.message.strip())

    return _sse(events())


@app.post("/v1/approve", response_model=TurnResponse)
def post_approve(body: ApproveRequest) -> TurnResponse:
    """Approve the pending create_booking / cancel_booking for this thread."""
    agent = get_agent()
    with _lock:
        result = approve(agent, body.thread_id, decision="approve")
    if result.status == "error" and result.error and "No pending" in result.error:
        raise HTTPException(status_code=409, detail=result.error)
    return _to_response(result)


@app.post("/v1/approve/stream")
def post_approve_stream(body: ApproveRequest) -> StreamingResponse:
    agent = get_agent()

    def events() -> Iterator[dict[str, Any]]:
        with _lock:
            yield from iter_approve_events(agent, body.thread_id, decision="approve")

    return _sse(events())


@app.post("/v1/reject", response_model=TurnResponse)
def post_reject(body: RejectRequest) -> TurnResponse:
    """Reject the pending action (no booking/cancel is executed)."""
    agent = get_agent()
    with _lock:
        result = approve(
            agent,
            body.thread_id,
            decision="reject",
            reason=body.reason,
        )
    if result.status == "error" and result.error and "No pending" in result.error:
        raise HTTPException(status_code=409, detail=result.error)
    return _to_response(result)


@app.post("/v1/reject/stream")
def post_reject_stream(body: RejectRequest) -> StreamingResponse:
    agent = get_agent()

    def events() -> Iterator[dict[str, Any]]:
        with _lock:
            yield from iter_approve_events(
                agent,
                body.thread_id,
                decision="reject",
                reason=body.reason,
            )

    return _sse(events())


@app.get("/v1/threads", response_model=list[ThreadSummary])
def get_threads() -> list[ThreadSummary]:
    """List past conversations (from checkpointer), newest first."""
    agent = get_agent()
    with _lock:
        items = list_threads(agent, limit=40)
    return [ThreadSummary(**item) for item in items]


@app.get("/v1/threads/{thread_id}", response_model=ThreadHistoryResponse)
def get_thread(thread_id: str) -> ThreadHistoryResponse:
    """Load message history so the UI can resume a past chat."""
    agent = get_agent()
    with _lock:
        data = get_thread_history(agent, thread_id)
    return ThreadHistoryResponse(**data)


@app.get("/v1/threads/{thread_id}/pending", response_model=TurnResponse)
def get_thread_pending(thread_id: str) -> TurnResponse:
    agent = get_agent()
    with _lock:
        result = get_pending(agent, thread_id)
    return _to_response(result)
