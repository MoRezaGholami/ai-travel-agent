"""Pydantic request/response models for the travel API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str | None = Field(
        default=None,
        description="Reuse to continue the same conversation / HITL interrupt",
    )


class PendingActionOut(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class TurnResponse(BaseModel):
    thread_id: str
    status: Literal["ok", "needs_approval", "error"]
    reply: str | None = None
    pending: list[PendingActionOut] = Field(default_factory=list)
    error: str | None = None


class ApproveRequest(BaseModel):
    thread_id: str
    reason: str | None = None


class RejectRequest(BaseModel):
    thread_id: str
    reason: str | None = "User rejected the action."
