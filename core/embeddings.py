"""Embedding service for agent discovery using OpenAI text-embedding-3-small."""

import os
import logging
from typing import Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.agent import Agent

logger = logging.getLogger(__name__)

from config import settings as _settings
OPENAI_API_KEY = _settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


def build_composite_text(agent: Agent) -> str:
    """Build composite text from agent fields for embedding."""
    parts = [agent.name or ""]
    if agent.description:
        parts.append(agent.description)
    if agent.skills:
        skill_tags = [s.skill_tag for s in agent.skills if s.skill_tag]
        categories = list({s.category for s in agent.skills if s.category})
        if skill_tags:
            parts.append(f"Skills: {', '.join(skill_tags)}")
        if categories:
            parts.append(f"Category: {', '.join(categories)}")
    return " | ".join(parts)


async def embed_text(text_input: str) -> Optional[list[float]]:
    """Embed text using OpenAI text-embedding-3-small. Returns vector or None on failure."""
    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set, skipping embedding")
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"input": text_input, "model": EMBEDDING_MODEL},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error("Failed to embed text: %s", e)
        return None


async def embed_texts_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed multiple texts in one API call."""
    if not OPENAI_API_KEY or not texts:
        return [None] * len(texts)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"input": texts, "model": EMBEDDING_MODEL},
            )
            resp.raise_for_status()
            data = resp.json()
            # API returns sorted by index
            results: list[Optional[list[float]]] = [None] * len(texts)
            for item in data["data"]:
                results[item["index"]] = item["embedding"]
            return results
    except Exception as e:
        logger.error("Batch embedding failed: %s", e)
        return [None] * len(texts)


async def embed_and_store_agent(db: AsyncSession, agent: Agent) -> bool:
    """Generate embedding for an agent and store it in the database."""
    composite = build_composite_text(agent)
    embedding = await embed_text(composite)
    if embedding is None:
        return False

    vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
    await db.execute(
        text("UPDATE agents SET description_embedding = CAST(:vec AS vector) WHERE id = :agent_id"),
        {"vec": vec_str, "agent_id": str(agent.id)},
    )
    return True


async def batch_embed_agents(db: AsyncSession, agents: list[Agent], batch_size: int = 50) -> int:
    """Embed a batch of agents. Returns count of successfully embedded."""
    count = 0
    for i in range(0, len(agents), batch_size):
        batch = agents[i : i + batch_size]
        texts = [build_composite_text(a) for a in batch]
        embeddings = await embed_texts_batch(texts)
        for agent, embedding in zip(batch, embeddings):
            if embedding is not None:
                vec_str = "[" + ",".join(str(v) for v in embedding) + "]"
                await db.execute(
                    text("UPDATE agents SET description_embedding = CAST(:vec AS vector) WHERE id = :agent_id"),
                    {"vec": vec_str, "agent_id": str(agent.id)},
                )
                count += 1
        await db.flush()
    return count
