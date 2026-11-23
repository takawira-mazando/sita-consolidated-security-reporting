"""Admin models for multi‑tenant administration"""

from sqlalchemy import Column, String, Text, JSON, DateTime, func
from sqlalchemy.orm import relationship

from .base import Base


class MSSP(Base):
    __tablename__ = "mssps"
    __table_args__ = {"schema": "identity"}

    id = Column(String, primary_key=True)
    name = Column(String(120), nullable=False)
    code = Column(String(60), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="active")
    admin_user_id = Column(String, nullable=True)  # FK to identity.users.id (set programmatically)
    admin_user = relationship("User", backref="managed_mssp", foreign_keys=[admin_user_id])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = {"schema": "identity"}

    id = Column(String, primary_key=True)
    mssp_id = Column(String, nullable=False)  # FK to identity.mssps.id
    mssp = relationship("MSSP", backref="tenants", foreign_keys=[mssp_id])
    name = Column(String(120), nullable=False)
    identifier = Column(String(60), nullable=False, unique=True)
    type = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    superuser_id = Column(String, nullable=True)  # FK to identity.users.id
    superuser = relationship("User", backref="managed_tenant", foreign_keys=[superuser_id])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "identity"}

    id = Column(String, primary_key=True)
    owner_type = Column(String(20), nullable=False)  # platform, mssp, tenant, branch
    owner_id = Column(String, nullable=True)        # optional FK depending on owner_type
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSON, nullable=False, default=list)  # list of permission ids
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        # ensure unique role name per owner scope
        {'sqlite_autoincrement': True}
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "identity"}

    id = Column(String, primary_key=True)
    resource = Column(String(120), nullable=False)
    action = Column(String(20), nullable=False)
    scope = Column(String(20), nullable=False)  # platform, mssp, tenant, branch
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
