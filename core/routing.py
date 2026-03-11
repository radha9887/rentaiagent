from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.task import Task


async def route_task(db: AsyncSession, task_id: UUID) -> Task:
    """Phase 1A stub: just update task status to 'routed'. Actual HTTP forwarding in Phase 1C."""
    task = (await db.execute(select(Task).where(Task.id == task_id))).scalar_one()
    task.status = "routed"
    task.routed_at = datetime.now(timezone.utc)
    await db.flush()
    return task
