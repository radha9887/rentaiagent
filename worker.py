from celery import Celery
from config import settings

celery_app = Celery("rentaiagent", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "health-check-agents": {
            "task": "check_all_agents_health",
            "schedule": 300.0,  # every 5 minutes
        },
    },
)

# Register tasks
import tasks.health  # noqa: F401
