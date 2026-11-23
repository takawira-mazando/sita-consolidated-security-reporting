import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)

from app.models.base import Base, TimestampMixin
from app.pii_crypto import EncryptedText


class Person(Base, TimestampMixin):
    """LDAP-sourced identity record for a platform user.

    Persons are imported from the configured directory. Role/scope assignment
    lives on the linked identity.users row and is managed by platform admins.

    ``id`` is an internal UUID and is the only key an account references.
    The LDAP directory identifier is held as an :class:`EmploymentIdentifier`
    row against this record so a directory identifier is not used as the
    account's primary key.

    See ``app.employment`` for scheme definitions and validation.
    """

    __tablename__ = "persons"
    __table_args__ = (
        CheckConstraint(
            "source IN ('ldap', 'active_directory', 'directory')",
            name="ck_persons_ldap_source",
        ),
        {"schema": "identity"},
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_number = Column(String(50), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    #: SA national identity number. Stored AES-256-GCM encrypted at rest via a
    #: TypeDecorator, so it is encrypted on write and decrypted on read without
    #: any query or serialiser needing to know. The GCM tag is bound to this
    #: column name, so a ciphertext moved from one employee's row onto another
    #: fails to decrypt rather than authenticating silently.
    #:
    #: The physical column is TEXT, not VARCHAR(20): the stored form is an
    #: envelope, not a 13-digit string.
    id_number = Column(EncryptedText("identity.persons.id_number"))
    title = Column(String(20))
    initials = Column(String(20))
    surname = Column(String(100))
    display_name = Column(String(100))
    job_title = Column(String(120))
    org_unit = Column(String(120))
    department_id = Column(String(36), index=True)
    branch_id = Column(String(36))
    manager_id = Column(String(36))
    manager_name = Column(String(120))
    work_phone = Column(String(30))
    location = Column(String(120))
    employment_status = Column(String(30), default="active")
    clearance_level = Column(String(30))
    source = Column(String(20), default="ldap")
    is_active = Column(Boolean, nullable=False, default=True)


class EmploymentIdentifier(Base):
    """An LDAP directory identifier linked to an internal person record.

    LDAP identifiers are unique by scheme and value, so a directory account
    cannot resolve to multiple person records.

    Personal identity numbers remain in ``Person.id_number`` and are not used
    for account resolution.
    """

    __tablename__ = "employment_identifier"
    __table_args__ = (
        UniqueConstraint("scheme", "value", name="uq_employment_identifier_scheme_value"),
        CheckConstraint("scheme = 'ldap'", name="ck_employment_identifier_ldap_only"),
        {"schema": "identity"},
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    person_id = Column(
        String(36),
        ForeignKey("identity.persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme = Column(String(32), nullable=False, index=True)
    value = Column(String(64), nullable=False, index=True)
    #: The configured directory that supplied the identifier.
    source_system = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
