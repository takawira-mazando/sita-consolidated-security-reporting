import enum

from sqlalchemy import Column, Date, DateTime, Numeric, String, func

from app.models.base import Base


class RiskBucket(str, enum.Enum):
    SAFE = "safe"
    MONITORED = "monitored"
    CRITICAL = "critical"

class RiskScore(Base):
    __tablename__ = "risk_scores"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    app_name = Column(String(255), nullable=False)
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    score_date = Column(Date, nullable=False)
    fused_score = Column(Numeric(5, 1), nullable=False)
    signal_appscan = Column(Numeric(5, 1))
    signal_imperva = Column(Numeric(5, 1))
    signal_api_exposure = Column(Numeric(5, 1))
    signal_compliance_penalty = Column(Numeric(5, 1))
    bucket = Column(String(20))
    computed_at = Column(DateTime(timezone=True), server_default=func.now())
