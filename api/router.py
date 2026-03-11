from fastapi import APIRouter
from api import auth, agents, credits, tasks, ratings, admin, agent_ratings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(credits.router)
api_router.include_router(tasks.router)
api_router.include_router(ratings.router)
api_router.include_router(admin.router)
api_router.include_router(agent_ratings.router)
