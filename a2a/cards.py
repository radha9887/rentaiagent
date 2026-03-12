"""Agent Card generation for A2A protocol."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from models.agent import Agent, AgentSkill
from utils.errors import NotFoundError

router = APIRouter()

PLATFORM_CARD = {
    "name": "RentAnAgent Marketplace",
    "description": "AI agent marketplace — discover, rent, and orchestrate agents via A2A protocol",
    "url": "https://rentanagent.io",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {"id": "agent-discovery", "name": "Agent Discovery", "description": "Search and discover available AI agents"},
        {"id": "task-routing", "name": "Task Routing", "description": "Route tasks to the best-matched agent"},
    ],
    "authentication": {"schemes": ["bearer"]},
    "defaultInputModes": ["application/json"],
    "defaultOutputModes": ["application/json"],
    "provider": {
        "organization": "RentAnAgent Marketplace",
        "url": "https://rentanagent.io",
    },
}


@router.get("/.well-known/agent.json")
async def platform_agent_card():
    return PLATFORM_CARD


@router.get("/a2a/agents/{slug}/agent.json")
async def agent_card(slug: str, db: AsyncSession = Depends(get_db)):
    agent = (await db.execute(select(Agent).where(Agent.slug == slug))).scalar_one_or_none()
    if not agent:
        raise NotFoundError("Agent not found")

    skills = []
    for s in agent.skills or []:
        skills.append({
            "id": s.skill_tag,
            "name": s.skill_tag,
            "description": f"{s.skill_tag} (category: {s.category or 'general'})",
        })

    stats_ext = {}
    if agent.stats:
        stats_ext = {
            "total_tasks": agent.stats.total_tasks,
            "completed_tasks": agent.stats.completed_tasks,
            "avg_rating": agent.stats.avg_rating,
            "avg_response_ms": agent.stats.avg_response_ms,
        }

    card = {
        "name": agent.name,
        "description": agent.description or "",
        "url": agent.endpoint_url or "",
        "version": agent.version or "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "skills": skills,
        "authentication": {"schemes": ["bearer"]},
        "defaultInputModes": ["application/json"],
        "defaultOutputModes": ["application/json"],
        "provider": {
            "organization": "RentAnAgent Marketplace",
            "url": "https://rentanagent.io",
        },
        "x-rentanagent": {
            "pricing": {
                "model": agent.pricing_model,
                "price_per_task": float(agent.price_per_task) if agent.price_per_task else 0,
                "currency": agent.currency,
            },
            "stats": stats_ext,
            "trust_tier": agent.trust_tier,
        },
    }
    return card
