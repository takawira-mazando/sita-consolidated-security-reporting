from pydantic import BaseModel
from datetime import date
from typing import Optional

class ComplianceSnapshot(BaseModel):
    framework: str
    snapshot_date: date
    overall_score: float
    total_controls: int
    passed_controls: int
    details: Optional[dict] = None

class ComplianceGap(BaseModel):
    id: str
    framework: str
    control_id: str
    domain: Optional[str] = None
    description: str
    owner: Optional[str] = None
    severity: str
    due_date: Optional[date] = None
    status: str = "open"
