from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    has_more: bool = False
    total: Optional[int] = None


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
