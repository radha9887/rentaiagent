"""External agent discovery and verification via A2A protocol."""

from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.external_agent import ExternalAgent
from a2a.protocol import jsonrpc_request
from utils.errors import ValidationError, NotFoundError

logger = logging.getLogger(__name__)

REQUIRED_CARD_FIELDS = {"name", "url", "skills"}


async def fetch_agent_card(url: str) -> dict:
    """Fetch and validate an agent card from a URL.

    Args:
        url: Base URL of the agent (we append /.well-known/agent.json).

    Returns:
        Parsed agent card dict.

    Raises:
        ValidationError: If the card is missing required fields or unreachable.
    """
    card_url = url.rstrip("/") + "/.well-known/agent.json"
    logger.info("Fetching agent card from %s", card_url)

    try:
        async with httpx.AsyncClient(timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.get(card_url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning("Failed to fetch agent card from %s: %s", card_url, e)
        raise ValidationError(f"Could not fetch agent card: {e}")

    try:
        card = resp.json()
    except Exception:
        raise ValidationError("Agent card is not valid JSON")

    missing = REQUIRED_CARD_FIELDS - set(card.keys())
    if missing:
        raise ValidationError(f"Agent card missing required fields: {missing}")

    if not isinstance(card.get("skills"), list) or len(card["skills"]) == 0:
        raise ValidationError("Agent card must have at least one skill")

    return card


async def verify_agent(card_url: str, card: dict) -> dict:
    """Verify an external agent is real and responsive.

    Sends a lightweight A2A health-check request to the agent's endpoint.

    Returns:
        Dict with keys: verified (bool), error (str|None), latency_ms (float).
    """
    endpoint = card.get("url", "").rstrip("/")
    if not endpoint:
        return {"verified": False, "error": "No endpoint URL in card", "latency_ms": 0}

    # Send a minimal JSON-RPC request to check the agent is alive
    rpc = jsonrpc_request(method="tasks/get", params={"id": "00000000-0000-0000-0000-000000000000"}, id="health-check")

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=settings.HEALTH_CHECK_TIMEOUT_SECONDS) as client:
            resp = await client.post(endpoint, json=rpc)
        latency_ms = (time.monotonic() - start) * 1000

        # We expect a valid JSON-RPC response (even an error response is fine — it means the agent is alive)
        data = resp.json()
        if "jsonrpc" not in data:
            return {"verified": False, "error": "Response is not valid JSON-RPC", "latency_ms": latency_ms}

        return {"verified": True, "error": None, "latency_ms": latency_ms}

    except httpx.TimeoutException:
        return {"verified": False, "error": "Agent timed out", "latency_ms": 0}
    except Exception as e:
        return {"verified": False, "error": str(e), "latency_ms": 0}


async def refresh_agent_card(db: AsyncSession, external_agent_id: UUID) -> ExternalAgent:
    """Re-fetch and update the cached agent card for an external agent.

    Returns:
        Updated ExternalAgent instance.

    Raises:
        NotFoundError: If the external agent record doesn't exist.
    """
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == external_agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")

    card = await fetch_agent_card(ext.agent_card_url)

    ext.agent_card_cache = card
    ext.name = card.get("name", ext.name)
    ext.description = card.get("description", "")
    ext.endpoint_url = card.get("url", ext.endpoint_url)
    ext.skills = card.get("skills", [])
    ext.card_last_fetched_at = datetime.now(timezone.utc)

    # Extract protocols from capabilities
    protocols = ["a2a"]
    if card.get("capabilities", {}).get("streaming"):
        protocols.append("streaming")
    ext.protocols = protocols

    await db.flush()
    logger.info("Refreshed agent card for external agent %s", external_agent_id)
    return ext


async def health_check_external(db: AsyncSession, external_agent_id: UUID) -> bool:
    """Check if an external agent is still healthy.

    Updates health_status, health_last_checked_at, and counters.

    Returns:
        True if healthy, False otherwise.
    """
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == external_agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")

    result = await verify_agent(ext.agent_card_url, ext.agent_card_cache or {})
    ext.health_last_checked_at = datetime.now(timezone.utc)
    ext.health_check_count = (ext.health_check_count or 0) + 1

    if result["verified"]:
        ext.health_status = "healthy"
        ext.health_fail_count = 0
        logger.info("External agent %s is healthy (%.0fms)", ext.name, result["latency_ms"])
    else:
        ext.health_fail_count = (ext.health_fail_count or 0) + 1
        ext.health_status = "unhealthy"
        logger.warning("External agent %s health check failed: %s", ext.name, result["error"])

    await db.flush()
    return result["verified"]
