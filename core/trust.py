from models.rating import AgentStats


def calculate_trust_tier(stats: AgentStats) -> str:
    if stats.completed_tasks >= 500 and stats.avg_rating >= 4.8:
        return "platinum"
    if stats.completed_tasks >= 200 and stats.avg_rating >= 4.5:
        return "gold"
    if stats.completed_tasks >= 50 and stats.avg_rating >= 4.0:
        return "silver"
    if stats.completed_tasks >= 10 and stats.avg_rating >= 3.5:
        return "bronze"
    return "new"
