from math import ceil

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1, le=200)
    pages: int = 0

    def __init__(self, **data):
        super().__init__(**data)
        if self.pages == 0 and self.size > 0:
            self.pages = ceil(self.total / self.size)

class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None
