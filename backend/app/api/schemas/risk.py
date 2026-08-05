from datetime import date, datetime

from pydantic import BaseModel, Field


class RiskScore(BaseModel):
    app_name: str
    score_date: date
    fused_score: float = Field(..., ge=0, le=100)
    signal_appscan: float | None = None
    signal_imperva: float | None = None
    signal_api_exposure: float | None = None
    signal_compliance_penalty: float | None = None
    bucket: str
    computed_at: datetime

class RiskTrend(BaseModel):
    app_name: str
    trend: list[RiskScore]
