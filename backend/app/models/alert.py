import enum

from sqlalchemy import JSON, Column, DateTime, Integer, String, func

from app.models.base import Base


class AlertStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    rule_id = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String)
    severity = Column(String(20), nullable=False)
    source = Column(String(100))
    target_id = Column(String(255))
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    status = Column(String(20), default="new")
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime(timezone=True))
    enriched_data = Column(JSON)
    channels = Column(JSON)
    dedup_key = Column(String(190))
    dedup_count = Column(Integer, default=1)
    first_triggered = Column(DateTime(timezone=True), nullable=False)
    last_triggered = Column(DateTime(timezone=True), nullable=False)
    last_dispatched_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class DispatchStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class DispatchLog(Base):
    __tablename__ = "dispatch_log"
    __table_args__ = {"schema": "warehouse"}

    id = Column(String, primary_key=True)
    alert_id = Column(String(64), index=True, nullable=False)
    channel = Column(String(20), nullable=False)
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    status = Column(String(20), nullable=False, default="sent")
    error = Column(String)
    attempted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
