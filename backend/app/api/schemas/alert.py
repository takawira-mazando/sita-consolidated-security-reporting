from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Alert(BaseModel):
    id: str
    rule_id: str
    title: str
    description: Optional[str] = None
    severity: str
    source: Optional[str] = None
    target_id: Optional[str] = None
    status: str
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    first_triggered: datetime
    last_triggered: datetime
    created_at: datetime
