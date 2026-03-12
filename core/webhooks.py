"""Webhook delivery system — POST task events to subscriber callback URLs."""

from __future__ import annotations
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.webhook import WebhookSubscription
from models.task import Task

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 10


def _sign_payload(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def trigger_webhook(db: AsyncSession, task_id: UUID, event: str) -> None:
    """Find matching webhook subscriptions and POST to their callback URLs.

    Matches subscriptions by task_id (exact) or user_id (if task_id is null on subscription).
    Retries up to WEBHOOK_MAX_RETRIES times with exponential backoff.
    Deactivates subscriptions after MAX_CONSECUTIVE_FAILURES consecutive failures.
    """
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one_or_none()
    if not task:
        logger.warning("trigger_webhook: task %s not found", task_id)
        return

    # Find subscriptions: matching this specific task, or user-wide (task_id IS NULL)
    subs = (await db.execute(
        select(WebhookSubscription).where(
            WebhookSubscription.is_active == True,
            or_(
                WebhookSubscription.task_id == task_id,
                WebhookSubscription.task_id.is_(None),
            ),
            WebhookSubscription.user_id == task.requester_user_id,
        )
    )).scalars().all()

    for sub in subs:
        if event not in (sub.events or []):
            continue

        payload = json.dumps({
            "event": event,
            "task_id": str(task_id),
            "task_status": task.status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).encode()

        signature = _sign_payload(payload, sub.secret)
        headers = {
            "Content-Type": "application/json",
            "X-RentAnAgent-Signature": signature,
            "X-RentAnAgent-Event": event,
        }

        delivered = False
        max_retries = settings.WEBHOOK_MAX_RETRIES

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECONDS) as client:
                    resp = await client.post(sub.callback_url, content=payload, headers=headers)
                    resp.raise_for_status()

                delivered = True
                sub.last_triggered_at = datetime.now(timezone.utc)
                sub.failure_count = 0
                logger.info("Webhook delivered: event=%s sub=%s url=%s", event, sub.id, sub.callback_url)
                break

            except Exception as e:
                wait = 2 ** attempt
                logger.warning(
                    "Webhook delivery attempt %d/%d failed for sub %s: %s (retry in %ds)",
                    attempt + 1, max_retries, sub.id, e, wait,
                )
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(wait)

        if not delivered:
            sub.failure_count = (sub.failure_count or 0) + 1
            logger.error("Webhook delivery failed after %d attempts for sub %s", max_retries, sub.id)

            if sub.failure_count >= MAX_CONSECUTIVE_FAILURES:
                sub.is_active = False
                logger.warning("Deactivated webhook subscription %s after %d consecutive failures", sub.id, sub.failure_count)

    await db.flush()
