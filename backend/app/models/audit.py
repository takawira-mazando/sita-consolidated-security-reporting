import uuid

from sqlalchemy import JSON, Column, DateTime, String, func

from app.models.base import Base


class ActionAudit(Base):
    """Immutable action trail (audit schema).

    Records privileged/export actions for non-repudiation. The Auditor-General
    export engine writes one row per signed attestation, binding the SHA-256
    integrity hash to the actor and tenant scope so tampering is detectable.
    """

    __tablename__ = "action_audit"
    __table_args__ = {"schema": "audit"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(255), nullable=False)
    action = Column(String(50), nullable=False)
    target = Column(String(255))
    tenant_scope = Column(JSON)
    payload_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
