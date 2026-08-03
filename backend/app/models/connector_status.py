from sqlalchemy import Column, String, Integer, DateTime
from app.models.base import Base

class ConnectorHealth(Base):
    __tablename__ = "connector_health"
    __table_args__ = {"schema": "warehouse"}

    name = Column(String(50), primary_key=True)
    source = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="healthy")
    last_poll_at = Column(DateTime(timezone=True))
    last_success_at = Column(DateTime(timezone=True))
    latency_ms = Column(Integer)
    events_per_hour = Column(Integer)
    error_count = Column(Integer, default=0)
    circuit_state = Column(String(20), default="closed")
