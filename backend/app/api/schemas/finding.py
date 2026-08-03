from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Finding(BaseModel):
    id: str
    source: str
    external_id: str
    app_name: str
    severity: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    status: str
    version: int = 1
