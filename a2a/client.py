"""A2A outbound client — sends tasks TO provider agents."""

from __future__ import annotations
import hashlib
import hmac
import json
import logging
from uuid import uuid4

import httpx

from config import settings
from models.agent import Agent
from models.task import Task
from a2a.protocol import (
    jsonrpc_request, A2A_TO_INTERNAL, DataPart, TextPart,
)

logger = logging.getLogger(__name__)


def _sign_body(body: bytes) -> str:
    """HMAC-SHA256 signature of the request body."""
    return hmac.new(settings.HMAC_SECRET.encode(), body, hashlib.sha256).hexdigest()


async def send_task_a2a(agent: Agent, task: Task) -> dict:
    """Send task to provider via A2A message/send."""
    parts = []
    if task.description:
        parts.append({"type": "text", "text": task.description})
    if task.payload:
        parts.append({"type": "data", "data": task.payload, "mimeType": "application/json"})

    rpc = jsonrpc_request(
        method="message/send",
        params={
            "message": {"parts": parts},
            "metadata": {
                "task_id": str(task.id),
                "skill": task.skill_requested,
            },
        },
        id=str(uuid4()),
    )

    body = json.dumps(rpc).encode()
    headers = {
        "Content-Type": "application/json",
        "X-RentAnAgent-Signature": _sign_body(body),
    }

    timeout = task.max_wait_seconds or 300
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(agent.endpoint_url, content=body, headers=headers)
        resp.raise_for_status()

    data = resp.json()

    # Parse A2A response
    if "error" in data:
        return {"status": "failed", "error": data["error"].get("message", "A2A error")}

    a2a_task = data.get("result", {})
    a2a_state = a2a_task.get("status", {}).get("state", "failed")
    internal_status = A2A_TO_INTERNAL.get(a2a_state, "failed")

    result = {"status": internal_status}

    artifacts = a2a_task.get("artifacts", [])
    if artifacts:
        # Flatten artifact parts into result data
        result_data = {}
        for artifact in artifacts:
            for part in artifact.get("parts", []):
                if part.get("type") == "data":
                    result_data.update(part.get("data", {}))
                elif part.get("type") == "text":
                    result_data["text"] = part.get("text", "")
        result["data"] = result_data

    return result


async def send_task_https(agent: Agent, task: Task) -> dict:
    """Fallback for non-A2A agents — simple POST."""
    payload = {
        "task_id": str(task.id),
        "skill": task.skill_requested,
        "description": task.description,
        "payload": task.payload,
    }
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-RentAnAgent-Signature": _sign_body(body),
    }

    timeout = task.max_wait_seconds or 300
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(agent.endpoint_url, content=body, headers=headers)
        resp.raise_for_status()

    return resp.json()


async def send_task_to_provider(agent: Agent, task: Task) -> dict:
    """Route task to provider using appropriate protocol."""
    try:
        protocols = agent.protocols or []
        if "a2a" in protocols:
            return await send_task_a2a(agent, task)
        else:
            return await send_task_https(agent, task)
    except httpx.TimeoutException:
        logger.warning("Timeout sending task %s to agent %s", task.id, agent.slug)
        return {"status": "timeout", "error": "Provider timed out"}
    except httpx.HTTPError as e:
        logger.error("HTTP error sending task %s to agent %s: %s", task.id, agent.slug, e)
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        logger.error("Unexpected error sending task %s to agent %s: %s", task.id, agent.slug, e)
        return {"status": "failed", "error": str(e)}
