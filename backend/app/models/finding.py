import enum

from sqlalchemy import JSON, Column, DateTime, Integer, String, UniqueConstraint, func

from app.models.base import Base


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
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    ministry_id = Column(String(36), index=True)
    cluster_id = Column(String(36), index=True)
    severity = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(String)
    category = Column(String(200))
    # Cross-source OWASP Top 10 classification. Additive: `category` above stays
    # exactly as the OEM sent it, because the vendor taxonomy remains useful for
    # anyone working in the vendor's own terms.
    owasp_id = Column(String(10), index=True)
    cwe_id = Column(String(20), index=True)
    owasp_status = Column(String(20))
    taxonomy_version = Column(String(32))
    raw_data = Column(JSON)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="open")
    version = Column(Integer, default=1)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
