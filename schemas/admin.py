from pydantic import BaseModel
from decimal import Decimal


class MetricsResponse(BaseModel):
    total_users: int
    total_agents: int
    total_tasks: int
    completed_tasks: int
    total_revenue: Decimal
