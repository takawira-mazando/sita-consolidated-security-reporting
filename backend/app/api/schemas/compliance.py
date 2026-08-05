from datetime import date

from pydantic import BaseModel


class ComplianceSnapshot(BaseModel):
    framework: str
    snapshot_date: date
    overall_score: float
    total_controls: int
    passed_controls: int
    details: dict | None = None

class ComplianceGap(BaseModel):
    id: str
    framework: str
    control_id: str
    domain: str | None = None
    description: str
    owner: str | None = None
    severity: str
    due_date: date | None = None
    status: str = "open"
