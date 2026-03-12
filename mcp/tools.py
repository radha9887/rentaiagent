"""MCP tool definitions and execution."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.escrow import hold_credits
from core.matching import build_agent_search_query
from core.routing import route_task
from models.agent import Agent, AgentSkill
from models.rating import Rating, AgentStats
from models.task import Task


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = []
_TOOL_MAP: dict[str, Any] = {}


def _register(name: str, description: str, schema: dict):
    """Decorator to register an MCP tool."""
    def decorator(fn):
        TOOL_DEFINITIONS.append({
            "name": name,
            "description": description,
            "inputSchema": schema,
        })
        _TOOL_MAP[name] = fn
        return fn
    return decorator


async def execute_tool(name: str, params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    fn = _TOOL_MAP.get(name)
    if fn is None:
        raise KeyError(f"Unknown tool: {name}")
    return await fn(params, user_id, db)


# ---------------------------------------------------------------------------
# search_agents
# ---------------------------------------------------------------------------

@_register(
    name="search_agents",
    description="Search the RentAnAgent marketplace for agents that have a specific skill. Returns matching agents with pricing, ratings, and availability.",
    schema={
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Skill tag to search for (e.g. 'summarization', 'translation')"},
            "query": {"type": "string", "description": "Free-text search query for agent descriptions"},
            "max_price": {"type": "number", "description": "Maximum price per task"},
            "min_rating": {"type": "number", "description": "Minimum average rating (1.0-5.0)"},
            "limit": {"type": "integer", "description": "Max results to return (default 5, max 20)", "default": 5, "maximum": 20},
        },
        "required": ["skill"],
    },
)
async def _search_agents(params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    limit = min(params.get("limit", 5), 20)
    query = build_agent_search_query(
        skill=params["skill"],
        q=params.get("query"),
        max_price=params.get("max_price"),
        min_rating=params.get("min_rating"),
    )
    query = query.limit(limit)
    result = await db.execute(query)
    agents = result.scalars().unique().all()

    return {
        "agents": [
            {
                "slug": a.slug,
                "name": a.name,
                "description": a.description,
                "pricing_model": a.pricing_model,
                "price_per_task": str(a.price_per_task),
                "currency": a.currency,
                "trust_tier": a.trust_tier,
                "skills": [{"tag": s.skill_tag, "category": s.category, "proficiency": s.proficiency} for s in a.skills],
                "stats": {
                    "avg_rating": a.stats.avg_rating if a.stats else 0,
                    "total_tasks": a.stats.total_tasks if a.stats else 0,
                    "completed_tasks": a.stats.completed_tasks if a.stats else 0,
                } if True else None,
            }
            for a in agents
        ],
        "count": len(agents),
    }


# ---------------------------------------------------------------------------
# post_task
# ---------------------------------------------------------------------------

@_register(
    name="post_task",
    description="Send a task to a specific agent on the marketplace. Requires credits. Returns the task ID and status.",
    schema={
        "type": "object",
        "properties": {
            "agent_slug": {"type": "string", "description": "Slug of the agent to send the task to"},
            "skill": {"type": "string", "description": "Skill being requested"},
            "payload": {"type": "object", "description": "Task payload (input data for the agent)"},
            "description": {"type": "string", "description": "Human-readable description of the task"},
            "max_wait_seconds": {"type": "integer", "description": "Max seconds to wait for completion (default 60, max 300)", "default": 60, "maximum": 300},
        },
        "required": ["agent_slug", "skill", "payload"],
    },
)
async def _post_task(params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    agent = (await db.execute(select(Agent).where(Agent.slug == params["agent_slug"]))).scalar_one_or_none()
    if not agent:
        raise ValueError(f"Agent '{params['agent_slug']}' not found")
    if agent.status != "online":
        raise ValueError(f"Agent '{params['agent_slug']}' is not online (status: {agent.status})")

    quoted_price = Decimal(str(agent.price_per_task))
    platform_fee = quoted_price * Decimal(str(15)) / Decimal("100")

    task = Task(
        id=uuid.uuid4(),
        requester_user_id=user_id,
        provider_agent_id=agent.id,
        skill_requested=params["skill"],
        description=params.get("description"),
        payload=params["payload"],
        max_wait_seconds=min(params.get("max_wait_seconds", 60), 300),
        quoted_price=quoted_price,
        platform_fee=platform_fee,
        status="pending",
    )
    db.add(task)
    await db.flush()

    escrow = await hold_credits(db, user_id, quoted_price, task.id)
    task.status = "escrowed"
    task.escrowed_at = datetime.now(timezone.utc)
    await db.flush()

    task = await route_task(db, task.id)
    await db.commit()

    return {
        "task_id": str(task.id),
        "status": task.status,
        "quoted_price": str(quoted_price),
        "platform_fee": str(platform_fee),
        "result": task.result,
    }


# ---------------------------------------------------------------------------
# check_task_status
# ---------------------------------------------------------------------------

@_register(
    name="check_task_status",
    description="Check the current status of a previously submitted task. Returns status, result if completed, or error if failed.",
    schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "UUID of the task to check"},
        },
        "required": ["task_id"],
    },
)
async def _check_task_status(params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    try:
        task_uuid = uuid.UUID(params["task_id"])
    except (ValueError, KeyError):
        raise ValueError("Invalid task_id")

    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise ValueError("Task not found")
    if task.requester_user_id != user_id:
        raise ValueError("Task does not belong to you")

    return {
        "task_id": str(task.id),
        "status": task.status,
        "result": task.result if task.status == "completed" else None,
        "error_message": task.error_message if task.status == "failed" else None,
    }


# ---------------------------------------------------------------------------
# rate_agent
# ---------------------------------------------------------------------------

@_register(
    name="rate_agent",
    description="Rate an agent after a task has been completed. Score must be between 1.0 and 5.0.",
    schema={
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "UUID of the completed task"},
            "score": {"type": "number", "description": "Rating score from 1.0 to 5.0", "minimum": 1.0, "maximum": 5.0},
            "feedback": {"type": "string", "description": "Optional text feedback about the agent"},
        },
        "required": ["task_id", "score"],
    },
)
async def _rate_agent(params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    try:
        task_uuid = uuid.UUID(params["task_id"])
    except (ValueError, KeyError):
        raise ValueError("Invalid task_id")

    task = (await db.execute(select(Task).where(Task.id == task_uuid))).scalar_one_or_none()
    if not task:
        raise ValueError("Task not found")
    if task.requester_user_id != user_id:
        raise ValueError("Task does not belong to you")
    if task.status != "completed":
        raise ValueError(f"Task is not completed (status: {task.status})")

    # Check for existing rating
    existing = (await db.execute(
        select(Rating).where(Rating.task_id == task_uuid, Rating.rater_user_id == user_id)
    )).scalar_one_or_none()
    if existing:
        raise ValueError("You already rated this task")

    score = float(params["score"])
    if not (1.0 <= score <= 5.0):
        raise ValueError("Score must be between 1.0 and 5.0")

    rating = Rating(
        id=uuid.uuid4(),
        task_id=task_uuid,
        rated_agent_id=task.provider_agent_id,
        rater_user_id=user_id,
        overall_score=score,
        feedback=params.get("feedback"),
    )
    db.add(rating)

    # Update agent stats
    stats = (await db.execute(
        select(AgentStats).where(AgentStats.agent_id == task.provider_agent_id)
    )).scalar_one_or_none()
    if stats:
        new_count = stats.rating_count + 1
        stats.avg_rating = ((stats.avg_rating * stats.rating_count) + score) / new_count
        stats.rating_count = new_count
    else:
        stats = AgentStats(
            agent_id=task.provider_agent_id,
            avg_rating=score,
            rating_count=1,
        )
        db.add(stats)

    await db.commit()

    return {
        "rating_id": str(rating.id),
        "message": "Rating submitted successfully",
    }


# ---------------------------------------------------------------------------
# hire_best_agent
# ---------------------------------------------------------------------------

@_register(
    name="hire_best_agent",
    description="Automatically find and hire the best available agent for a skill. The platform selects the optimal agent based on rating, price, speed, and availability.",
    schema={
        "type": "object",
        "properties": {
            "skill": {"type": "string", "description": "Skill needed (e.g. 'summarize', 'translate')"},
            "payload": {"type": "object", "description": "Task payload"},
            "priority": {"type": "string", "enum": ["balanced", "quality", "speed", "price"], "description": "What to optimize for"},
            "max_price": {"type": "number", "description": "Maximum price willing to pay"},
        },
        "required": ["skill"],
    },
)
async def _hire_best_agent(params: dict, user_id: uuid.UUID, db: AsyncSession) -> dict:
    from core.auto_select import select_ranked_agents
    from core.routing import route_task_with_failover

    preferences = {}
    if params.get("priority"):
        preferences["priority"] = params["priority"]
    if params.get("max_price") is not None:
        preferences["max_price"] = params["max_price"]

    ranked = await select_ranked_agents(db, params["skill"], preferences)
    if not ranked:
        raise ValueError(f"No available agent for skill '{params['skill']}'")

    best = ranked[0]
    quoted_price = Decimal(str(best.price_per_task))
    platform_fee = quoted_price * Decimal("15") / Decimal("100")

    task = Task(
        id=uuid.uuid4(),
        requester_user_id=user_id,
        provider_agent_id=best.id,
        skill_requested=params["skill"],
        description=f"Auto-selected agent for {params['skill']}",
        payload=params.get("payload"),
        max_wait_seconds=300,
        quoted_price=quoted_price,
        platform_fee=platform_fee,
        status="pending",
        metadata_={"auto_selected": True, "priority": params.get("priority", "balanced")},
    )
    db.add(task)
    await db.flush()

    escrow = await hold_credits(db, user_id, quoted_price, task.id)
    task.status = "escrowed"
    task.escrowed_at = datetime.now(timezone.utc)
    await db.flush()

    task = await route_task_with_failover(db, task, ranked, max_attempts=3)
    await db.commit()

    # Fetch the agent that actually handled it (may differ from best due to failover)
    assigned = (await db.execute(select(Agent).where(Agent.id == task.provider_agent_id))).scalar_one_or_none()

    return {
        "task_id": str(task.id),
        "status": task.status,
        "agent_slug": assigned.slug if assigned else None,
        "agent_name": assigned.name if assigned else None,
        "quoted_price": str(quoted_price),
        "platform_fee": str(platform_fee),
        "result": task.result,
    }
