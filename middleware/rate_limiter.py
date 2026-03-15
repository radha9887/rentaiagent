import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from config import Settings

settings = Settings()

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis sliding window rate limiter."""
    
    def __init__(self, app):
        super().__init__(app)
        self.redis = aioredis.from_url(settings.REDIS_URL)
    
    async def dispatch(self, request: Request, call_next):
        # Get client IP
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
        path = request.url.path
        method = request.method
        
        # Registration rate limit: 5 per IP per 24h
        if path == "/v1/auth/register" and method == "POST":
            key = f"rate:register:{ip}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 86400)  # 24 hours
            if count > 5:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many registrations. Maximum 5 per day. Try again later."}
                )
        
        # Login rate limit: 10 per IP per hour
        if path == "/v1/auth/login" and method == "POST":
            key = f"rate:login:{ip}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 3600)  # 1 hour
            if count > 10:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Too many login attempts. Try again in an hour."}
                )
        
        # General API rate limit: 100 per minute per IP
        if path.startswith("/v1/") and path not in ["/v1/stats", "/v1/tasks/feed", "/v1/agents/featured"]:
            key = f"rate:api:{ip}"
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, 60)  # 1 minute
            if count > 100:
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded. Maximum 100 requests per minute."}
                )
        
        response = await call_next(request)
        return response
