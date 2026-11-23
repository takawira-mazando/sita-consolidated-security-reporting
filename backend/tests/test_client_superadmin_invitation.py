from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routers import admin, auth
from app.models.client_organization import ClientOrganization
from app.models.client_superadmin_invitation import ClientSuperadminInvitation
from app.models.person import Person
from app.models.user import User
from app.security import hash_password, verify_password


class _Scalars:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return _Scalars(self.rows)


class _Session:
    def __init__(self, invitation, client, person):
        self.invitation = invitation
        self.client = client
        self.person = person
        self.added = []

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        if model is ClientSuperadminInvitation:
            rows = [self.invitation] if self.invitation.used_at is None else []
        elif model is User:
            rows = []
        else:
            rows = []
        return _Result(rows)

    async def get(self, model, _identifier):
        return {
            ClientOrganization: self.client,
            Person: self.person,
        }.get(model)

    def add(self, row):
        self.added.append(row)

    async def commit(self):
        return None

    async def rollback(self):
        return None


class _InviteSession:
    def __init__(self, client, existing_user=None):
        self.client = client
        self.existing_user = existing_user
        self.added = []
        self.commit_count = 0

    async def execute(self, statement):
        model = statement.column_descriptions[0]["entity"]
        rows = [self.existing_user] if model is User and self.existing_user else []
        return _Result(rows)

    async def get(self, model, _identifier):
        if model is not ClientOrganization:
            raise AssertionError(f"Unexpected lookup for {model.__name__}")
        return self.client

    def add(self, row):
        self.added.append(row)

    async def flush(self):
        return None

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, _row):
        return None

    async def rollback(self):
        return None


def _setup():
    email = "client.admin@example.test"
    person = Person(
        id="person-1",
        email=email,
        display_name="Client Administrator",
        source="ldap",
        employment_status="active",
        is_active=True,
    )
    client = ClientOrganization(
        id="client-1",
        identifier="sita",
        name="SITA",
        description="",
        client_type="enterprise",
        deployment_model="saas",
        status="active",
        status_options=["draft", "active"],
        primary_contact_name="Contact",
        primary_contact_email=email,
        superadmin_name="Client Administrator",
        superadmin_email=email,
        access_setup_status="pending_superadmin_setup",
    )
    invitation = ClientSuperadminInvitation(
        id="invitation-1",
        client_organization_id=client.id,
        person_id=person.id,
        email=email,
        token_hash="a" * 64,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        created_by="operator@example.test",
    )
    return invitation, client, person


@pytest.mark.asyncio
async def test_provider_provisions_temporary_client_superadmin_credentials(monkeypatch):
    _, client, _ = _setup()
    session = _InviteSession(client)
    delivered = {}

    def capture_email(**message):
        assert session.commit_count == 1
        delivered.update(message)

    async def ignore_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(admin, "send_client_superadmin_credentials", capture_email)
    monkeypatch.setattr(admin, "_audit_privilege_change", ignore_audit)

    response = await admin.provision_client_superadmin(
        client.id,
        None,
        session,
        SimpleNamespace(email="operator@example.test", roles=["operator"]),
    )

    user = next(row for row in session.added if isinstance(row, User))
    assert response["status"] == "credential_created"
    assert response["email"] == client.superadmin_email
    assert response["temporary_password"] == delivered["temporary_password"]
    assert verify_password(delivered["temporary_password"], user.password_hash)
    assert user.display_name == client.superadmin_name
    assert user.email == client.superadmin_email
    assert user.person_id is None
    assert user.roles == ["client-admin"]
    assert client.access_setup_status == "pending_client_workspace"


@pytest.mark.asyncio
async def test_provider_cannot_invite_superadmin_for_inactive_client():
    _, client, _ = _setup()
    client.status = "draft"

    with pytest.raises(HTTPException) as error:
        await admin.provision_client_superadmin(
            client.id,
            None,
            _InviteSession(client),
            SimpleNamespace(email="operator@example.test", roles=["operator"]),
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_provider_requires_designated_superadmin_profile_details():
    _, client, _ = _setup()
    client.superadmin_email = ""
    session = _InviteSession(client)

    with pytest.raises(HTTPException) as error:
        await admin.provision_client_superadmin(
            client.id,
            None,
            session,
            SimpleNamespace(email="operator@example.test", roles=["operator"]),
        )

    assert error.value.status_code == 409
    assert session.added == []


@pytest.mark.asyncio
async def test_provider_can_rotate_existing_client_superadmin_password(monkeypatch):
    _, client, _ = _setup()
    user = User(
        id="client-admin-1",
        email=client.superadmin_email,
        password_hash=hash_password("previous-temporary-password"),
        display_name=client.superadmin_name,
        roles=["client-admin"],
        person_id=None,
        is_active=True,
    )
    session = _InviteSession(client, existing_user=user)
    delivered = {}

    def capture_email(**message):
        assert session.commit_count == 1
        delivered.update(message)

    async def ignore_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(admin, "send_client_superadmin_credentials", capture_email)
    monkeypatch.setattr(admin, "_audit_privilege_change", ignore_audit)

    response = await admin.rotate_client_superadmin_password(
        client.id,
        None,
        session,
        SimpleNamespace(email="operator@example.test", roles=["operator"]),
    )

    assert response["status"] == "credential_rotated"
    assert response["email"] == client.superadmin_email
    assert response["temporary_password"] == delivered["temporary_password"]
    assert verify_password(response["temporary_password"], user.password_hash)
    assert not verify_password("previous-temporary-password", user.password_hash)


@pytest.mark.asyncio
async def test_provider_cannot_rotate_platform_admin_password():
    _, client, _ = _setup()
    user = User(
        id="platform-admin-1",
        email=client.superadmin_email,
        password_hash=hash_password("platform-admin-password"),
        display_name=client.superadmin_name,
        roles=["admin"],
        person_id=None,
        is_active=True,
    )
    session = _InviteSession(client, existing_user=user)

    with pytest.raises(HTTPException) as error:
        await admin.rotate_client_superadmin_password(
            client.id,
            None,
            session,
            SimpleNamespace(email="operator@example.test", roles=["operator"]),
        )

    assert error.value.status_code == 409
    assert verify_password("platform-admin-password", user.password_hash)


@pytest.mark.asyncio
async def test_invitation_completion_creates_client_scoped_admin_not_platform_admin(monkeypatch):
    invitation, client, person = _setup()
    session = _Session(invitation, client, person)

    async def ignore_audit(*_args, **_kwargs):
        return None

    monkeypatch.setattr(auth, "_audit_auth", ignore_audit)
    body = auth.CompleteClientSuperadminInvitation(
        token="x" * 43,
        password="a-strong-password-with-12+",
    )

    response = await auth.complete_client_superadmin_invitation(body, None, session)

    user = next(row for row in session.added if isinstance(row, User))
    assert response == {"status": "password_set", "email": person.email}
    assert user.roles == ["client-admin"]
    assert "admin" not in user.roles
    assert verify_password(body.password, user.password_hash)
    assert invitation.used_at is not None
    assert client.access_setup_status == "pending_client_workspace"


@pytest.mark.asyncio
async def test_invitation_completion_rejects_reuse(monkeypatch):
    invitation, client, person = _setup()
    invitation.used_at = datetime.now(timezone.utc)
    session = _Session(invitation, client, person)
    body = auth.CompleteClientSuperadminInvitation(
        token="x" * 43,
        password="a-strong-password-with-12+",
    )

    with pytest.raises(HTTPException) as error:
        await auth.complete_client_superadmin_invitation(body, None, session)

    assert error.value.status_code == 400
    assert session.added == []
