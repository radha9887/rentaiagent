#!/usr/bin/env python3
"""One-time backfill script to generate embeddings for all existing agents."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select, text
from db import async_session
from models.agent import Agent
from core.embeddings import batch_embed_agents


async def main():
    async with async_session() as db:
        # Get agents without embeddings
        result = await db.execute(
            select(Agent).where(
                text("description_embedding IS NULL")
            )
        )
        agents = list(result.scalars().unique().all())
        print(f"Found {len(agents)} agents without embeddings")

        if not agents:
            print("Nothing to do.")
            return

        count = await batch_embed_agents(db, agents, batch_size=50)
        await db.commit()
        print(f"Successfully embedded {count}/{len(agents)} agents")


if __name__ == "__main__":
    asyncio.run(main())
