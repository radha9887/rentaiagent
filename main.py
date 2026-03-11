from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import engine
from api.router import api_router
from mcp.server import router as mcp_router
from middleware.request_id import RequestIDMiddleware
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.logging import LoggingMiddleware
from utils.errors import AppError, app_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

# Middleware (order matters — outermost first)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)

# Routes
app.include_router(api_router)
app.include_router(mcp_router)

# A2A routes
from a2a.cards import router as a2a_cards_router
from a2a.server import router as a2a_server_router
app.include_router(a2a_cards_router)
app.include_router(a2a_server_router)


@app.get("/health")
async def health():
    errors = []
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"db: {e}")

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception as e:
        errors.append(f"redis: {e}")

    if errors:
        return {"status": "unhealthy", "errors": errors}
    return {"status": "healthy"}
