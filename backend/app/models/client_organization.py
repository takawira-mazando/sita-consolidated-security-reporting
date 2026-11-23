import uuid

from sqlalchemy import JSON, Column, DateTime, String, Text, func

from app.models.base import Base


class ClientOrganization(Base):
    __tablename__ = "client_organizations"
    __table_args__ = {"schema": "identity"}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=False, default="")
    client_type = Column(String(32), nullable=False)
    deployment_model = Column(String(32), nullable=False)
    status = Column(String(64), nullable=False, default="draft", index=True)
    status_options = Column(
        JSON,
        nullable=False,
        default=lambda: ["draft", "active", "inactive", "suspended", "archived"],
    )
    primary_contact_name = Column(String(128), nullable=False)
    primary_contact_email = Column(String(254), nullable=False)
    superadmin_name = Column(String(128), nullable=False)
    superadmin_email = Column(String(254), nullable=False)
    access_setup_status = Column(String(32), nullable=False, default="pending_client_workspace")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
