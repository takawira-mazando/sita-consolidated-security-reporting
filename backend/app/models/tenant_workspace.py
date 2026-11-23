import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, UniqueConstraint, func

from app.models.base import Base


class ClientTenantWorkspace(Base):
    __tablename__ = "client_tenant_workspaces"
    __table_args__ = (
        UniqueConstraint(
            "client_organization_id",
            "identifier",
            name="uq_client_tenant_workspace_identifier",
        ),
        Index("idx_client_tenant_workspaces_client", "client_organization_id"),
        {"schema": "identity"},
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_organization_id = Column(
        String(36),
        ForeignKey("identity.client_organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    identifier = Column(String(64), nullable=False)
    name = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    root_label = Column(String(64), nullable=False, default="Organization")
    administration_model = Column(String(24), nullable=False, default="mssp_managed")
    hierarchy_levels = Column(JSON, nullable=False, default=list)
    org_units = Column(JSON, nullable=False, default=list)
    roles = Column(JSON, nullable=False, default=list)
    assignments = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
