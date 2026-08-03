from sqlalchemy import Column, String, Integer, DateTime, JSON, Date, Numeric, func
from app.models.base import Base

class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    framework = Column(String(50), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    overall_score = Column(Numeric(5, 1), nullable=False)
    details = Column(JSON)
    total_controls = Column(Integer, nullable=False)
    passed_controls = Column(Integer, nullable=False)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

class ComplianceGap(Base):
    __tablename__ = "compliance_gaps"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    framework = Column(String(50), nullable=False)
    control_id = Column(String(50), nullable=False)
    domain = Column(String(100))
    description = Column(String, nullable=False)
    owner = Column(String(100))
    severity = Column(String(20))
    due_date = Column(Date)
    status = Column(String(30), default="open")
    evidence_count = Column(Integer, default=0)
