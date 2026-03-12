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
        # Retry once on timeout
        try:
            logger.info("Retrying task %s to agent %s", task.id, agent.slug)
            protocols = agent.protocols or []
            if "a2a" in protocols:
                return await send_task_a2a(agent, task)
            else:
                return await send_task_https(agent, task)
        except Exception:
            return {"status": "timeout", "error": "Provider timed out after retry"}
    except httpx.HTTPStatusError as e:
        # No retry on 4xx
        logger.error("HTTP %d sending task %s to agent %s: %s", e.response.status_code, task.id, agent.slug, e)
        return {"status": "failed", "error": str(e)}
    except httpx.HTTPError as e:
        logger.error("HTTP error sending task %s to agent %s: %s", task.id, agent.slug, e)
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        logger.error("Unexpected error sending task %s to agent %s: %s", task.id, agent.slug, e)
        return {"status": "failed", "error": str(e)}


async def send_task_a2a_external(ext_agent, task: Task) -> dict:
    """Send task to an external A2A agent (ExternalAgent model).

    Similar to send_task_a2a but works with ExternalAgent instances
    instead of internal Agent models.
    """
    from models.external_agent import ExternalAgent

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

    endpoint = ext_agent.endpoint_url
    if not endpoint:
        return {"status": "failed", "error": "External agent has no endpoint URL"}

    timeout = task.max_wait_seconds or 300

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(endpoint, content=body, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            return {"status": "failed", "error": data["error"].get("message", "A2A error")}

        a2a_task = data.get("result", {})
        a2a_state = a2a_task.get("status", {}).get("state", "failed")
        internal_status = A2A_TO_INTERNAL.get(a2a_state, "failed")

        result = {"status": internal_status}
        artifacts = a2a_task.get("artifacts", [])
        if artifacts:
            result_data = {}
            for artifact in artifacts:
                for part in artifact.get("parts", []):
                    if part.get("type") == "data":
                        result_data.update(part.get("data", {}))
                    elif part.get("type") == "text":
                        result_data["text"] = part.get("text", "")
            result["data"] = result_data

        return result

    except httpx.TimeoutException:
        # Retry once
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(endpoint, content=body, headers=headers)
                resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return {"status": "failed", "error": data["error"].get("message", "A2A error")}
            a2a_task = data.get("result", {})
            a2a_state = a2a_task.get("status", {}).get("state", "failed")
            return {"status": A2A_TO_INTERNAL.get(a2a_state, "failed")}
        except Exception:
            return {"status": "timeout", "error": "External agent timed out after retry"}
    except httpx.HTTPStatusError as e:
        return {"status": "failed", "error": f"HTTP {e.response.status_code}: {e}"}
    except Exception as e:
        logger.error("Error sending task to external agent %s: %s", ext_agent.name, e)
        return {"status": "failed", "error": str(e)}


async def send_task_a2a_streaming(endpoint_url: str, task: Task):
    """Send task via A2A sendSubscribe and yield SSE events.

    Yields dicts with state/message/artifacts as they arrive from the
    external agent's SSE stream.
    """
    parts = []
    if task.description:
        parts.append({"type": "text", "text": task.description})
    if task.payload:
        parts.append({"type": "data", "data": task.payload, "mimeType": "application/json"})

    rpc = jsonrpc_request(
        method="tasks/sendSubscribe",
        params={
            "message": {"parts": parts},
            "metadata": {"task_id": str(task.id), "skill": task.skill_requested},
        },
        id=str(uuid4()),
    )

    body = json.dumps(rpc).encode()
    headers = {
        "Content-Type": "application/json",
        "X-RentAnAgent-Signature": _sign_body(body),
        "Accept": "text/event-stream",
    }

    timeout = task.max_wait_seconds or 300

    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", endpoint_url, content=body, headers=headers) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        yield data
                    except json.JSONDecodeError:
                        logger.warning("Invalid SSE data: %s", line)
