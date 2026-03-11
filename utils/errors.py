from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"


class AuthError(AppError):
    status_code = 401
    detail = "Authentication failed"


class ForbiddenError(AppError):
    status_code = 403
    detail = "Forbidden"


class InsufficientCreditsError(AppError):
    status_code = 402
    detail = "Insufficient credits"


class ConflictError(AppError):
    status_code = 409
    detail = "Resource conflict"


class ValidationError(AppError):
    status_code = 422
    detail = "Validation error"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
