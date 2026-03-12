"""External agent registration and marketplace API endpoints."""

from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from api.deps import get_current_user, require_admin
from models.user import User
from models.external_agent import ExternalAgent
from a2a.discovery import fetch_agent_card, verify_agent, refresh_agent_card, health_check_external
from utils.errors import NotFoundError, ForbiddenError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/external-agents", tags=["external-agents"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class RegisterExternalAgentRequest(BaseModel):
    """Request body for registering an external agent."""
    card_url: str = Field(..., max_length=500, description="Base URL of the agent (we fetch /.well-known/agent.json)")


class ExternalAgentResponse(BaseModel):
    """Response schema for external agent records."""
    id: UUID
    name: str
    description: Optional[str] = None
    agent_card_url: str
    endpoint_url: Optional[str] = None
    verification_status: str
    health_status: str
    trust_tier: str
    is_listed: bool
    pricing_model: str
    price_per_task: Optional[float] = None
    currency: str
    protocols: Optional[list[str]] = None
    skills: Optional[list[dict]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

# TODO: Add rate limiting to registration endpoint

@router.post("/register", response_model=ExternalAgentResponse)
async def register_external_agent(
    body: RegisterExternalAgentRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Register an external agent by its agent card URL.

    Fetches the agent card, validates it, creates a record, and kicks off
    async verification.
    """
    try:
        card = await fetch_agent_card(body.card_url)
    except ValidationError:
        raise
    except Exception as e:
        logger.error("Failed to fetch agent card from %s: %s", body.card_url, e)
        raise ValidationError(f"Could not fetch agent card: {e}")

    # Check for duplicate registration
    existing = (await db.execute(
        select(ExternalAgent).where(
            ExternalAgent.agent_card_url == body.card_url,
            ExternalAgent.owner_id == user.id,
        )
    )).scalar_one_or_none()
    if existing:
        raise ValidationError("You have already registered this agent")

    ext = ExternalAgent(
        owner_id=user.id,
        agent_card_url=body.card_url,
        name=card.get("name", "Unknown Agent"),
        description=card.get("description", ""),
        endpoint_url=card.get("url", ""),
        agent_card_cache=card,
        card_last_fetched_at=datetime.now(timezone.utc),
        verification_status="pending",
        skills=card.get("skills", []),
        protocols=["a2a"],
    )

    # Extract pricing from card extensions
    pricing = card.get("x-rentanagent", {}).get("pricing", {})
    if pricing:
        ext.pricing_model = pricing.get("model", "per_task")
        ext.price_per_task = pricing.get("price_per_task")
        ext.currency = pricing.get("currency", "INR")

    db.add(ext)
    await db.flush()

    # Inline verification (for simplicity; in production, use a background task queue)
    try:
        result = await verify_agent(body.card_url, card)
        if result["verified"]:
            ext.verification_status = "verified"
            ext.health_status = "healthy"
            ext.is_listed = True
            logger.info("External agent %s verified successfully (%.0fms)", ext.name, result["latency_ms"])
        else:
            ext.verification_status = "failed"
            ext.verification_error = result["error"]
            logger.warning("External agent %s verification failed: %s", ext.name, result["error"])
    except Exception as e:
        ext.verification_status = "failed"
        ext.verification_error = str(e)
        logger.error("External agent %s verification error: %s", ext.name, e)

    await db.commit()
    await db.refresh(ext)
    return ext


@router.get("", response_model=list[ExternalAgentResponse])
async def list_external_agents(
    skill: Optional[str] = Query(None, description="Filter by skill name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List verified and listed external agents (public, no auth required)."""
    # TODO: Add rate limiting
    query = select(ExternalAgent).where(
        ExternalAgent.verification_status == "verified",
        ExternalAgent.is_listed == True,
    )

    if skill:
        # Search in JSONB skills array for matching skill name
        query = query.where(
            ExternalAgent.skills.op("@>")(f'[{{"name": "{skill}"}}]')
        )

    query = query.order_by(ExternalAgent.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{agent_id}", response_model=ExternalAgentResponse)
async def get_external_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get external agent details."""
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")
    return ext


@router.post("/{agent_id}/verify", response_model=ExternalAgentResponse)
async def verify_external_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """Admin: trigger re-verification of an external agent."""
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")

    try:
        ext = await refresh_agent_card(db, ext.id)
        result = await verify_agent(ext.agent_card_url, ext.agent_card_cache or {})
        if result["verified"]:
            ext.verification_status = "verified"
            ext.verification_error = None
            ext.health_status = "healthy"
            ext.is_listed = True
        else:
            ext.verification_status = "failed"
            ext.verification_error = result["error"]
    except Exception as e:
        ext.verification_status = "failed"
        ext.verification_error = str(e)

    await db.commit()
    await db.refresh(ext)
    return ext


@router.delete("/{agent_id}")
async def delete_external_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove an external agent listing. Owner or admin only."""
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")

    if ext.owner_id != user.id and user.role != "admin":
        raise ForbiddenError("Only the owner or an admin can delete this agent")

    await db.delete(ext)
    await db.commit()
    return {"detail": "External agent removed"}


@router.get("/{agent_id}/card")
async def get_external_agent_card(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the cached agent card in A2A format."""
    ext = (await db.execute(
        select(ExternalAgent).where(ExternalAgent.id == agent_id)
    )).scalar_one_or_none()
    if not ext:
        raise NotFoundError("External agent not found")

    if not ext.agent_card_cache:
        raise NotFoundError("No cached agent card available")

    return ext.agent_card_cache
