import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, func

from app.models.base import Base


class ClientSuperadminInvitation(Base):
    __tablename__ = "client_superadmin_invitations"
    __table_args__ = (
        Index("idx_client_superadmin_invitations_client", "client_organization_id"),
        Index("idx_client_superadmin_invitations_person", "person_id"),
        {"schema": "identity"},
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_organization_id = Column(
        String(36),
        ForeignKey("identity.client_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    person_id = Column(
        String(36),
        ForeignKey("identity.persons.id", ondelete="RESTRICT"),
        nullable=False,
    )
    email = Column(String(255), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
