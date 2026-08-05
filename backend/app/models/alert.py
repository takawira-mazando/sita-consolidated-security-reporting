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
    status = Column(String(20), default="new")
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime(timezone=True))
    enriched_data = Column(JSON)
    dedup_key = Column(String(64))
    dedup_count = Column(Integer, default=1)
    first_triggered = Column(DateTime(timezone=True), nullable=False)
    last_triggered = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
