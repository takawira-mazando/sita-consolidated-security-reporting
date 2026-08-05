from datetime import datetime

from pydantic import BaseModel


class Finding(BaseModel):
    id: str
    source: str
    external_id: str
    app_name: str
    severity: str
    title: str
    description: str | None = None
    category: str | None = None
    first_seen: datetime
    last_seen: datetime
    status: str
    version: int = 1
