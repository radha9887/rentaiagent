"""A2A protocol message types and helpers (Google A2A spec)."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from uuid import UUID

# ── A2A Task States ──────────────────────────────────────────────────────────

A2A_STATES = {"submitted", "working", "completed", "failed", "canceled"}

INTERNAL_TO_A2A: dict[str, str] = {
    "pending": "submitted",
    "escrowed": "submitted",
    "routed": "working",
    "processing": "working",
    "completed": "completed",
    "failed": "failed",
    "timeout": "failed",
    "cancelled": "canceled",
}

A2A_TO_INTERNAL: dict[str, str] = {
    "submitted": "pending",
    "working": "processing",
    "completed": "completed",
    "failed": "failed",
    "canceled": "cancelled",
}


# ── Part types ───────────────────────────────────────────────────────────────

@dataclass
class TextPart:
    text: str
    type: str = "text"

@dataclass
class DataPart:
    data: dict[str, Any]
    mimeType: str = "application/json"
    type: str = "data"

@dataclass
class FilePart:
    file: dict[str, str]  # {"uri": ..., "mimeType": ...}
    type: str = "file"


# ── Artifact ─────────────────────────────────────────────────────────────────

@dataclass
class Artifact:
    name: str
    parts: list[dict[str, Any]] = field(default_factory=list)


# ── TaskStatus ───────────────────────────────────────────────────────────────

@dataclass
class TaskStatus:
    state: str
    message: Optional[str] = None


# ── Builders ─────────────────────────────────────────────────────────────────

def build_a2a_task(
    task_id: str | UUID,
    state: str,
    message: Optional[str] = None,
    artifacts: list[dict] | None = None,
    history: list[dict] | None = None,
) -> dict[str, Any]:
    """Build an A2A Task response object."""
    result: dict[str, Any] = {
        "id": str(task_id),
        "status": {"state": state},
    }
    if message:
        result["status"]["message"] = message
    if artifacts:
        result["artifacts"] = artifacts
    if history:
        result["history"] = history
    return result


def build_a2a_task_from_internal(task) -> dict[str, Any]:
    """Build A2A task from an internal Task model instance."""
    state = INTERNAL_TO_A2A.get(task.status, "failed")
    artifacts = []
    if task.result:
        parts = []
        if isinstance(task.result, dict):
            parts.append(asdict(DataPart(data=task.result)))
        else:
            parts.append(asdict(TextPart(text=str(task.result))))
        artifacts.append({"name": "result", "parts": parts})
    return build_a2a_task(
        task_id=task.id,
        state=state,
        message=task.error_message,
        artifacts=artifacts or None,
    )


# ── JSON-RPC 2.0 helpers ────────────────────────────────────────────────────

def jsonrpc_request(method: str, params: dict[str, Any], id: str | int = 1) -> dict:
    return {"jsonrpc": "2.0", "method": method, "params": params, "id": id}


def jsonrpc_response(result: Any, id: str | int = 1) -> dict:
    return {"jsonrpc": "2.0", "result": result, "id": id}


def jsonrpc_error(code: int, message: str, id: str | int | None = None, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "error": err, "id": id}


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
