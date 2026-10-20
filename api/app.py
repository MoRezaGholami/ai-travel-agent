"""FastAPI app — chat + HITL approve/reject for the travel orchestrator.

Run:
  .\\.venv\\Scripts\\python.exe -m api
  # or: uvicorn api.app:app --reload --port 8000
"""

from __future__ import annotations

import threading
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.orchestrator import create_travel_orchestrator
from agent.session import TurnResult, approve, chat, get_pending
from api.schemas import (
    ApproveRequest,
    ChatRequest,
    RejectRequest,
    TurnResponse,
)

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent": "ready" if _agent is not None else "loading"}


@app.post("/v1/chat", response_model=TurnResponse)
def post_chat(body: ChatRequest) -> TurnResponse:
    """Send a user message. Returns reply or needs_approval + pending tool args."""
    thread_id = body.thread_id or str(uuid.uuid4())
    agent = get_agent()
    with _lock:
        result = chat(agent, thread_id, body.message.strip())
    return _to_response(result)


@app.post("/v1/approve", response_model=TurnResponse)
def post_approve(body: ApproveRequest) -> TurnResponse:
    """Approve the pending create_booking / cancel_booking for this thread."""
    agent = get_agent()
    with _lock:
        result = approve(agent, body.thread_id, decision="approve")
    if result.status == "error" and result.error and "No pending" in result.error:
        raise HTTPException(status_code=409, detail=result.error)
    return _to_response(result)


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


@app.get("/v1/threads/{thread_id}/pending", response_model=TurnResponse)
def get_thread_pending(thread_id: str) -> TurnResponse:
    agent = get_agent()
    with _lock:
        result = get_pending(agent, thread_id)
    return _to_response(result)
