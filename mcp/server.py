"""MCP SSE server — GET /mcp/sse + POST /mcp/messages."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, async_session
from api.deps import get_current_user
from models.user import User
from mcp.protocol import (
    MCPRequest,
    build_initialize_result,
    build_tools_list,
    error_response,
    success_response,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from mcp.tools import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger("mcp")

router = APIRouter(prefix="/mcp", tags=["mcp"])

# In-memory session store: session_id → {user_id, queue, last_active}
_sessions: dict[str, dict[str, Any]] = {}

SESSION_TIMEOUT = 30 * 60  # 30 minutes
HEARTBEAT_INTERVAL = 30  # seconds


def _cleanup_stale_sessions():
    now = time.time()
    stale = [sid for sid, s in _sessions.items() if now - s["last_active"] > SESSION_TIMEOUT]
    for sid in stale:
        _sessions.pop(sid, None)


# ---------------------------------------------------------------------------
# SSE endpoint
# ---------------------------------------------------------------------------

@router.get("/sse")
async def sse_endpoint(request: Request, user: User = Depends(get_current_user)):
    _cleanup_stale_sessions()

    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _sessions[session_id] = {"user_id": user.id, "queue": queue, "last_active": time.time()}

    async def event_generator():
        # Send endpoint event
        yield {"event": "endpoint", "data": f"/mcp/messages?session_id={session_id}"}

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                    yield {"event": "message", "data": json.dumps(msg)}
                except asyncio.TimeoutError:
                    # heartbeat
                    yield {"comment": "keepalive"}
        finally:
            _sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Message endpoint
# ---------------------------------------------------------------------------

@router.post("/messages")
async def messages_endpoint(
    request: Request,
    session_id: str = Query(...),
):
    session = _sessions.get(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Session not found"})

    session["last_active"] = time.time()

    try:
        body = await request.json()
    except Exception:
        await session["queue"].put(error_response(None, INVALID_REQUEST, "Invalid JSON"))
        return JSONResponse(status_code=202, content={"status": "accepted"})

    try:
        req = MCPRequest.from_dict(body)
    except (ValueError, KeyError):
        await session["queue"].put(error_response(body.get("id"), INVALID_REQUEST, "Invalid JSON-RPC 2.0 request"))
        return JSONResponse(status_code=202, content={"status": "accepted"})

    # Dispatch
    method = req.method
    user_id = session["user_id"]

    if method == "initialize":
        response = success_response(req.id, build_initialize_result())

    elif method == "notifications/initialized":
        # No response needed for notifications
        return JSONResponse(status_code=202, content={"status": "accepted"})

    elif method == "tools/list":
        response = success_response(req.id, build_tools_list(TOOL_DEFINITIONS))

    elif method == "tools/call":
        params = req.params or {}
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            response = error_response(req.id, INVALID_PARAMS, "Missing tool name")
        else:
            try:
                async with async_session() as db:
                    result = await execute_tool(tool_name, tool_args, user_id, db)
                response = success_response(req.id, {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": False,
                })
            except KeyError as e:
                response = error_response(req.id, METHOD_NOT_FOUND, str(e))
            except ValueError as e:
                response = error_response(req.id, INVALID_PARAMS, str(e))
            except Exception as e:
                logger.exception("Tool execution error")
                response = error_response(req.id, INTERNAL_ERROR, f"Internal error: {type(e).__name__}: {e}")

    else:
        response = error_response(req.id, METHOD_NOT_FOUND, f"Unknown method: {method}")

    await session["queue"].put(response)
    return JSONResponse(status_code=202, content={"status": "accepted"})
