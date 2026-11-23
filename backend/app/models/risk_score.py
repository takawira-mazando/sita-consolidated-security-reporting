import enum

from sqlalchemy import Column, Date, DateTime, Index, Numeric, String, func, text

from app.models.base import Base
from app.models.tenant_data_scope import TenantDataScope


class RiskBucket(str, enum.Enum):
    SAFE = "safe"
    MONITORED = "monitored"
    CRITICAL = "critical"

class RiskScore(TenantDataScope, Base):
    __tablename__ = "risk_scores"
    __table_args__ = (
        Index(
            "uq_risk_global_app_date",
            "app_name",
            "score_date",
            unique=True,
            postgresql_where=text("tenant_workspace_id IS NULL"),
        ),
        Index(
            "uq_risk_tenant_app_date",
            "tenant_workspace_id",
            "tenant_scope_level_key",
            "app_name",
            "score_date",
            unique=True,
            postgresql_where=text("tenant_workspace_id IS NOT NULL"),
        ),
        {"schema": "warehouse"},
    )

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
