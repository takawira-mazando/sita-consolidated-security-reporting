from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum, UniqueConstraint, func
from app.models.base import Base
import enum

class Severity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        UniqueConstraint("source", "external_id"),
        {"schema": "warehouse"},
    )

    id = Column(String, primary_key=True)
    source = Column(String(100), nullable=False)
    external_id = Column(String(255), nullable=False)
    app_name = Column(String(255), nullable=False, default="unknown")
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String)
    category = Column(String(200))
    raw_data = Column(JSON)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="open")
    version = Column(Integer, default=1)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
