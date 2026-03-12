"""Webhook subscription management API endpoints."""

from __future__ import annotations
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from api.deps import get_current_user
from models.user import User
from models.webhook import WebhookSubscription
from core.webhooks import trigger_webhook
from utils.errors import NotFoundError, ForbiddenError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

VALID_EVENTS = {"task.completed", "task.failed", "task.progress", "task.created", "task.cancelled"}


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreateWebhookRequest(BaseModel):
    """Request to create a webhook subscription."""
    callback_url: str = Field(..., max_length=500)
    events: list[str] = Field(..., min_length=1)
    task_id: Optional[UUID] = None


class WebhookResponse(BaseModel):
    """Webhook subscription response."""
    id: UUID
    callback_url: str
    events: list[str]
    task_id: Optional[UUID] = None
    is_active: bool
    failure_count: int
    secret: str
    created_at: datetime
    last_triggered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Endpoints ────────────────────────────────────────────────────────────────

# TODO: Add rate limiting

@router.post("", response_model=WebhookResponse)
async def create_webhook(
    body: CreateWebhookRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a webhook subscription for task events."""
    invalid = set(body.events) - VALID_EVENTS
    if invalid:
        raise ValidationError(f"Invalid events: {invalid}. Valid: {VALID_EVENTS}")

    sub = WebhookSubscription(
        user_id=user.id,
        task_id=body.task_id,
        callback_url=body.callback_url,
        events=body.events,
        secret=secrets.token_urlsafe(32),
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List my webhook subscriptions."""
    result = await db.execute(
        select(WebhookSubscription)
        .where(WebhookSubscription.user_id == user.id)
        .order_by(WebhookSubscription.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a webhook subscription."""
    sub = (await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    )).scalar_one_or_none()
    if not sub:
        raise NotFoundError("Webhook subscription not found")
    if sub.user_id != user.id:
        raise ForbiddenError("Not your subscription")

    await db.delete(sub)
    await db.commit()
    return {"detail": "Webhook subscription removed"}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a test event to a webhook subscription."""
    sub = (await db.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
    )).scalar_one_or_none()
    if not sub:
        raise NotFoundError("Webhook subscription not found")
    if sub.user_id != user.id:
        raise ForbiddenError("Not your subscription")

    # Send test payload using the webhook's secret
    import hashlib, hmac, json
    payload = json.dumps({
        "event": "test",
        "task_id": str(sub.task_id) if sub.task_id else None,
        "task_status": "test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }).encode()

    signature = hmac.new(sub.secret.encode(), payload, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-RentAnAgent-Signature": signature,
        "X-RentAnAgent-Event": "test",
    }

    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(sub.callback_url, content=payload, headers=headers)
            resp.raise_for_status()
        return {"detail": "Test event delivered", "status_code": resp.status_code}
    except Exception as e:
        return {"detail": f"Test event delivery failed: {e}", "status_code": None}
