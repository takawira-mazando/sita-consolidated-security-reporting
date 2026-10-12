import uuid

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, func

from app.models.base import Base


class ActionAudit(Base):
    """Append-only action trail (audit schema).

    Records privileged/export actions for non-repudiation. The Auditor-General
    export engine writes one row per signed attestation, binding the SHA-256
    integrity hash to the actor and tenant scope so tampering is detectable.

    Immutability is enforced by the database (REVOKE + append-only trigger in
    ``infrastructure/scripts/init-db.sql``), not by convention.

    The columns beyond the original seven exist so an action can be reconstructed
    long after the fact:

    - ``signature`` + ``signed_payload`` + ``key_id``: what was actually signed,
      so verification never depends on a lookup alone.
    - ``actor_role`` + ``policy_version`` + ``scope_hash``: the control state that
      was in force at decision time, which is what an auditor asks for first and
      what a bare timestamp cannot answer.
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

    # --- cryptographic evidence -------------------------------------------
    # Canonical bytes that were signed. Retained so verification is a local
    # signature check rather than a trusted-database lookup.
    signed_payload = Column(Text)
    signature = Column(Text)
    key_id = Column(String(64))
    signing_algorithm = Column(String(32))

    # --- control state at decision time -----------------------------------
    actor_role = Column(String(64))
    policy_version = Column(String(32))
    scope_hash = Column(String(64))

    # --- verification bookkeeping -----------------------------------------
    verification_status = Column(String(128))
    verified_at = Column(DateTime(timezone=True))
    verified_by = Column(String(255))
    attestation_size_bytes = Column(Integer)