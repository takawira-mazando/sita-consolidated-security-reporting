import uuid

from sqlalchemy import Boolean, Column, String

from app.models.base import Base, TimestampMixin


class Person(Base, TimestampMixin):
    """HR-sourced identity record for a platform user.

    Persons are provisioned from the HR system (PERSAL/payroll or SCIM feed)
    keyed on a stable employee_number. Role/scope assignment lives on the
    linked identity.users row and is never touched by HR sync.
    """

    __tablename__ = "persons"
    __table_args__ = {"schema": "identity"}

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_number = Column(String(50), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    id_number = Column(String(20))
    title = Column(String(20))
    initials = Column(String(20))
    surname = Column(String(100))
    display_name = Column(String(100))
    job_title = Column(String(120))
    org_unit = Column(String(120))
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36), index=True)
    manager_id = Column(String(36))
    manager_name = Column(String(120))
    work_phone = Column(String(30))
    location = Column(String(120))
    employment_status = Column(String(30), default="active")
    clearance_level = Column(String(30))
    source = Column(String(20), default="hr")
    is_active = Column(Boolean, nullable=False, default=True)
