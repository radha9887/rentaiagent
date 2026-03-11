"""A2A JSON-RPC server — receives tasks from external A2A agents."""

from __future__ import annotations
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from api.deps import get_current_user
from models.user import User
from models.agent import Agent
from models.task import Task
from models.credit import Escrow
from core.escrow import hold_credits, release_escrow, refund_escrow
from core.routing import route_task
from a2a.protocol import (
    jsonrpc_response, jsonrpc_error, build_a2a_task_from_internal,
    PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR,
)
from utils.errors import AppError

router = APIRouter()


@router.post("/a2a/agents/{slug}")
async def a2a_endpoint(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Parse JSON-RPC
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(jsonrpc_error(PARSE_ERROR, "Parse error"), status_code=200)

    jsonrpc = body.get("jsonrpc")
    method = body.get("method")
    params = body.get("params", {})
    req_id = body.get("id")

    if jsonrpc != "2.0" or not method:
        return JSONResponse(jsonrpc_error(INVALID_REQUEST, "Invalid JSON-RPC request", id=req_id), status_code=200)

    # Look up agent
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        return JSONResponse(jsonrpc_error(INVALID_PARAMS, f"Agent '{slug}' not found", id=req_id), status_code=200)

    try:
        if method == "message/send":
            result = await _handle_message_send(db, user, agent, params)
        elif method == "tasks/get":
            result = await _handle_tasks_get(db, user, params)
        elif method == "tasks/cancel":
            result = await _handle_tasks_cancel(db, user, params)
        else:
            return JSONResponse(jsonrpc_error(METHOD_NOT_FOUND, f"Method '{method}' not found", id=req_id), status_code=200)
    except AppError as e:
        return JSONResponse(jsonrpc_error(INTERNAL_ERROR, str(e.detail), id=req_id), status_code=200)
    except Exception as e:
        return JSONResponse(jsonrpc_error(INTERNAL_ERROR, str(e), id=req_id), status_code=200)

    return JSONResponse(jsonrpc_response(result, id=req_id), status_code=200)


async def _handle_message_send(db: AsyncSession, user: User, agent: Agent, params: dict) -> dict:
    """Process message/send — create and route a task."""
    message = params.get("message", {})
    parts = message.get("parts", [])

    # Extract text and data from parts
    description = ""
    payload = {}
    for part in parts:
        ptype = part.get("type", "")
        if ptype == "text":
            description += part.get("text", "")
        elif ptype == "data":
            payload.update(part.get("data", {}))

    skill = payload.pop("skill", None) or (agent.skills[0].skill_tag if agent.skills else "general")
    price = agent.price_per_task or Decimal("0")

    task = Task(
        requester_user_id=user.id,
        provider_agent_id=agent.id,
        skill_requested=skill,
        description=description or "A2A task",
        payload=payload or None,
        payload_size_bytes=len(str(payload).encode()),
        quoted_price=price,
        currency=agent.currency,
        status="pending",
    )
    db.add(task)
    await db.flush()

    # Escrow
    if price > 0:
        await hold_credits(db, user.id, price, task.id)
        task.status = "escrowed"
        await db.flush()

    # Route
    task = await route_task(db, task.id)
    await db.commit()

    return build_a2a_task_from_internal(task)


async def _handle_tasks_get(db: AsyncSession, user: User, params: dict) -> dict:
    """Return task status in A2A format."""
    task_id = params.get("id")
    if not task_id:
        raise AppError(status_code=400, detail="Missing task id")

    task = (await db.execute(select(Task).where(Task.id == UUID(task_id)))).scalar_one_or_none()
    if not task:
        raise AppError(status_code=404, detail="Task not found")
    if task.requester_user_id != user.id:
        raise AppError(status_code=403, detail="Not your task")

    return build_a2a_task_from_internal(task)


async def _handle_tasks_cancel(db: AsyncSession, user: User, params: dict) -> dict:
    """Cancel task and refund escrow."""
    task_id = params.get("id")
    if not task_id:
        raise AppError(status_code=400, detail="Missing task id")

    task = (await db.execute(select(Task).where(Task.id == UUID(task_id)))).scalar_one_or_none()
    if not task:
        raise AppError(status_code=404, detail="Task not found")
    if task.requester_user_id != user.id:
        raise AppError(status_code=403, detail="Not your task")

    if task.status in ("pending", "escrowed", "routed"):
        # Refund escrow if held
        escrow = (await db.execute(select(Escrow).where(Escrow.task_id == task.id, Escrow.status == "held"))).scalar_one_or_none()
        if escrow:
            await refund_escrow(db, escrow.id)

        task.status = "cancelled"
        await db.commit()

    return build_a2a_task_from_internal(task)
