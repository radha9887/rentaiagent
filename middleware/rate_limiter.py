from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Stub rate limiter — structure only, no actual Redis calls yet."""

    async def dispatch(self, request: Request, call_next):
        # TODO: Implement Redis sliding window rate limiting
        # key = f"rate:{api_key}"
        # current = await redis.incr(key)
        # if first: await redis.expire(key, window)
        # if current > limit: return 429
        return await call_next(request)
