from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

class RiskScore(BaseModel):
    app_name: str
    score_date: date
    fused_score: float = Field(..., ge=0, le=100)
    signal_appscan: Optional[float] = None
    signal_imperva: Optional[float] = None
    signal_api_exposure: Optional[float] = None
    signal_compliance_penalty: Optional[float] = None
    bucket: str
    computed_at: datetime

class RiskTrend(BaseModel):
    app_name: str
    trend: list[RiskScore]
