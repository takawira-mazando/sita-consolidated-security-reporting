from sqlalchemy import JSON, Boolean, Column, DateTime, String, func

from app.models.base import Base


class RejectedRecord(Base):
    __tablename__ = "rejected_records"
    __table_args__ = {"schema": "staging"}

    id = Column(String, primary_key=True)
    batch_id = Column(String, nullable=False)
    source = Column(String(100), nullable=False)
    raw_payload = Column(JSON, nullable=False)
    rejection_reason = Column(String, nullable=False)
    rejection_code = Column(String(20), nullable=False)
    rejected_at = Column(DateTime(timezone=True), server_default=func.now())
    reprocessed = Column(Boolean, default=False)
    reprocessed_at = Column(DateTime(timezone=True))
    ttl_expires_at = Column(DateTime(timezone=True), nullable=False)
