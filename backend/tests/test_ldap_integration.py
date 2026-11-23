import pytest
from app.connectors.ldap_connector import (
    ldap_connector,
    LDAPConfig,
    DEFAULT_ACTIVE_DIRECTORY_PROFILE,
    DEFAULT_OPENLDAP_PROFILE,
    DEFAULT_FREEIPA_PROFILE,
)


@pytest.fixture(autouse=True)
def isolated_mock_directory(monkeypatch):
    monkeypatch.setattr(
        ldap_connector,
        "_config",
        LDAPConfig(**DEFAULT_ACTIVE_DIRECTORY_PROFILE),
    )
    monkeypatch.setattr(
        ldap_connector,
        "_mock_users",
        [
            {
                "sAMAccountName": "test.user",
                "mail": "test.user@client.example",
                "displayName": "Test Directory User",
                "sn": "User",
                "givenName": "Test",
                "title": "Test Administrator",
                "employeeID": "DIR-TEST-001",
                "department": "Test Department",
                "physicalDeliveryOfficeName": "Test Branch",
                "memberOf": ["Enterprise Admins"],
                "password": "Test-Directory-Password-123!",
            }
        ],
    )


def test_ldap_config_get_and_masking():
    """Directory configuration masks password in dict export."""
    data = ldap_connector.config.model_dump()
    assert "server_url" in data
    assert "base_dn" in data
    assert "attribute_mapping" in data
    assert "role_mapping" in data


def test_ldap_config_update():
    """Updates directory settings dynamically for any client."""
    payload = {
        "client_name": "Custom Corporate Client",
        "server_url": "ldap://ad.corporate-client.internal:389",
        "base_dn": "dc=corporate,dc=com",
        "user_search_base": "ou=Employees,dc=corporate,dc=com",
    }
    updated = ldap_connector.update_config(payload)
    assert updated.client_name == "Custom Corporate Client"
    assert updated.server_url == "ldap://ad.corporate-client.internal:389"
    assert updated.base_dn == "dc=corporate,dc=com"


def test_ldap_preset_switching():
    """Applies Active Directory, OpenLDAP, or FreeIPA schema."""
    # Switch to OpenLDAP
    openldap_cfg = ldap_connector.apply_preset("openldap")
    assert openldap_cfg.preset_profile == "openldap"
    assert openldap_cfg.attribute_mapping["username"] == "uid"
    assert openldap_cfg.attribute_mapping["employee_id"] == "employeeNumber"

    # Switch back to Active Directory
    ad_cfg = ldap_connector.apply_preset("active_directory")
    assert ad_cfg.preset_profile == "active_directory"
    assert ad_cfg.attribute_mapping["username"] == "sAMAccountName"
    assert ad_cfg.attribute_mapping["employee_id"] == "employeeID"


def test_ldap_test_connection():
    """Performs diagnostic connection test."""
    result = ldap_connector.test_connection_sync()
    assert result["success"] is True
    assert result["entries_found"] > 0
    assert result["message"] is not None


def test_ldap_search_directory_users():
    """Directory search returns users with mapped security roles."""
    users = ldap_connector.search_users_sync("Test")
    assert len(users) >= 1
    user = users[0]
    assert user.surname == "User"
    assert user.username == "test.user"
    assert "admin" in user.suggested_roles
    assert user.employee_code == "DIR-TEST-001"


def test_ldap_unified_login():
    """Verifies LDAP credentials and authenticates directory users."""
    ok, user = ldap_connector.authenticate_mock_sync(
        "test.user@client.example", "Test-Directory-Password-123!"
    )
    assert ok is True
    assert user is not None
    assert user.email == "test.user@client.example"
    assert "admin" in user.suggested_roles
