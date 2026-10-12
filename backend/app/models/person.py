import uuid

from sqlalchemy import (
    Boolean,
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
    """HR-sourced identity record for a platform user.

    Persons are provisioned from an external HR system. Role/scope assignment
    lives on the linked identity.users row and is never touched by HR sync.

    ``id`` is an internal UUID and is the only key an account references.
    Authoritative external identifiers — PERSAL number, SAP personnel number,
    and the originating feed's own identifier — are held as
    :class:`EmploymentIdentifier` rows against this record. Keeping them
    separate means a corrected or reissued government number does not require
    re-keying an account, and it allows one person to carry several schemes at
    once (a PERSAL number from the national feed and a SAP personnel number from
    SITA's own HCM).

    See ``app.employment`` for scheme definitions and validation.
    """

    __tablename__ = "persons"
    __table_args__ = {"schema": "identity"}

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
    source = Column(String(20), default="hr")
    is_active = Column(Boolean, nullable=False, default=True)


class EmploymentIdentifier(Base):
    """A scheme-qualified external identifier for one employment record.

    One person may hold several identifiers across schemes, and a scheme may in
    principle be re-issued. Uniqueness is therefore enforced per
    ``(scheme, value)`` globally — two different people must never resolve to
    the same government identifier — while ``(person_id, scheme, value)`` is the
    natural key that makes re-ingesting the same feed idempotent.

    Deliberately *not* modelled here: the SA identity number. That identifies
    the person rather than the employment and is retained only on
    ``Person.id_number`` under the controls in ``app.pii``. Making it an
    employment identifier would both collide across reappointment and import
    the estate's most sensitive unique identifier (POPIA s.13(c), s.57) into
    account resolution.
    """

    __tablename__ = "employment_identifier"
    __table_args__ = (
        UniqueConstraint("scheme", "value", name="uq_employment_identifier_scheme_value"),
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
    #: The system the identifier was ingested from, e.g. "persal", "sita-sap-hcm".
    source_system = Column(String(64))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
