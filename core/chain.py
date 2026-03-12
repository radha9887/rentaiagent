"""Multi-hop task chain management — create and query subtask trees."""

from __future__ import annotations
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.task import Task
from models.task_chain import TaskChain
from models.agent import Agent
from models.credit import CreditAccount
from core.escrow import hold_credits
from core.routing import route_task
from utils.errors import ValidationError, NotFoundError, ForbiddenError

logger = logging.getLogger(__name__)


async def create_subtask(
    db: AsyncSession,
    parent_task_id: UUID,
    provider_agent_id: UUID,
    skill: str,
    payload: dict,
) -> Task:
    """Create a child task in a task chain.

    The child task is linked to the parent and root tasks. Escrow is held
    from the parent task's provider's credit account.

    Args:
        db: Database session.
        parent_task_id: The parent task that is spawning this subtask.
        provider_agent_id: The agent to route the subtask to.
        skill: The skill being requested.
        payload: Task payload data.

    Returns:
        The created and routed child Task.

    Raises:
        NotFoundError: If parent task or provider agent not found.
        ValidationError: If chain depth or breadth limits exceeded.
    """
    # 1. Get parent task
    parent = (await db.execute(select(Task).where(Task.id == parent_task_id))).scalar_one_or_none()
    if not parent:
        raise NotFoundError("Parent task not found")

    # 2. Determine root_task_id
    root_task_id = parent.root_task_id or parent.id

    # 3. Check max depth
    new_depth = (parent.hop_depth or 0) + 1
    if new_depth > settings.MAX_CHAIN_DEPTH:
        raise ValidationError(f"Maximum chain depth of {settings.MAX_CHAIN_DEPTH} exceeded")

    # 4. Check max breadth (count existing children of this parent)
    child_count = (await db.execute(
        select(func.count()).select_from(TaskChain).where(TaskChain.parent_task_id == parent_task_id)
    )).scalar() or 0
    if child_count >= settings.MAX_CHAIN_BREADTH:
        raise ValidationError(f"Maximum chain breadth of {settings.MAX_CHAIN_BREADTH} exceeded")

    # Get provider agent
    provider = (await db.execute(select(Agent).where(Agent.id == provider_agent_id))).scalar_one_or_none()
    if not provider:
        raise NotFoundError("Provider agent not found")

    price = provider.price_per_task or Decimal("0")

    # 5. Create child task
    child = Task(
        requester_user_id=parent.requester_user_id,
        requester_agent_id=parent.provider_agent_id,  # The parent's provider is requesting
        provider_agent_id=provider_agent_id,
        skill_requested=skill,
        description=payload.get("description", f"Subtask: {skill}"),
        payload=payload,
        payload_size_bytes=len(str(payload).encode()),
        quoted_price=price,
        currency=provider.currency,
        status="pending",
        parent_task_id=parent_task_id,
        root_task_id=root_task_id,
        hop_depth=new_depth,
        is_subtask=True,
    )
    db.add(child)
    await db.flush()

    # 6. Create TaskChain record
    chain = TaskChain(
        root_task_id=root_task_id,
        parent_task_id=parent_task_id,
        child_task_id=child.id,
        depth=new_depth,
    )
    db.add(chain)
    await db.flush()

    # 7. Escrow from the parent task's provider's owner credits
    parent_provider = (await db.execute(select(Agent).where(Agent.id == parent.provider_agent_id))).scalar_one_or_none()
    if parent_provider and price > 0:
        await hold_credits(db, parent_provider.owner_id, price, child.id)
        child.status = "escrowed"
        await db.flush()

    # 8. Route the child task
    child = await route_task(db, child.id)
    await db.flush()

    logger.info(
        "Created subtask %s (depth=%d) under parent %s, root %s",
        child.id, new_depth, parent_task_id, root_task_id,
    )
    return child


async def get_task_chain(db: AsyncSession, root_task_id: UUID) -> list[dict]:
    """Get full task chain tree for a root task.

    Returns a tree structure: [{task_id, status, depth, children: [...]}].
    """
    # Get all chain records for this root
    chains = (await db.execute(
        select(TaskChain)
        .where(TaskChain.root_task_id == root_task_id)
        .order_by(TaskChain.depth)
    )).scalars().all()

    # Get root task
    root = (await db.execute(select(Task).where(Task.id == root_task_id))).scalar_one_or_none()
    if not root:
        raise NotFoundError("Root task not found")

    # Build lookup of task_id -> task info
    all_task_ids = {root_task_id} | {c.child_task_id for c in chains}
    tasks = (await db.execute(select(Task).where(Task.id.in_(all_task_ids)))).scalars().all()
    task_map = {t.id: t for t in tasks}

    # Build parent -> children mapping
    children_map: dict[UUID, list[UUID]] = {}
    for c in chains:
        children_map.setdefault(c.parent_task_id, []).append(c.child_task_id)

    def _build_node(task_id: UUID) -> dict:
        """Recursively build a tree node."""
        t = task_map.get(task_id)
        node = {
            "task_id": str(task_id),
            "status": t.status if t else "unknown",
            "skill": t.skill_requested if t else None,
            "depth": t.hop_depth if t else 0,
            "children": [],
        }
        for child_id in children_map.get(task_id, []):
            node["children"].append(_build_node(child_id))
        return node

    return [_build_node(root_task_id)]
