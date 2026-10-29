from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from app.config import settings
from app.db import get_session
from app.main import app
from app.connectors.external_hr import persal_api, sita_employee_api


def create_token(email: str, roles: list[str], depts: list[str] | None = None) -> str:
    return jwt.encode(
        {
            "sub": "user-" + email.split("@")[0],
            "email": email,
            "roles": roles,
            "department_ids": depts or [],
            "branch_ids": [],
            "province_ids": [],
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


@pytest.fixture
def admin_headers():
    token = create_token("admin@sita.co.za", ["admin"])
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_sita_employee_api_data_minimization():
    """Verify SITA Employee System API returns ONLY surname, position, and employee code."""
    res = await sita_employee_api.lookup("SIT-00101")
    assert res is not None
    assert res.employee_code == "SIT-00101"
    assert res.surname == "Mthembu"
    assert res.position == "SITA Command Center Superadmin & Lead Security Architect"
    assert res.department_id == "sita"
    assert res.source_system == "sita-sap-hcm"
    assert res.scheme == "sap_personnel"

    # Upstream HR master fields MUST NOT exist on the platform identity
    assert not hasattr(res, "_upstream_id_number")
    assert not hasattr(res, "_upstream_salary_band")
    assert not hasattr(res, "_upstream_residential_address")


@pytest.mark.asyncio
async def test_persal_api_data_minimization():
    """Verify PERSAL API returns ONLY surname, position, and PERSAL number."""
    res = await persal_api.lookup("80491024")
    assert res is not None
    assert res.employee_code == "80491024"
    assert res.surname == "Mazibuko"
    assert "DHA Department Superadmin" in res.position
    assert res.department_id == "home-affairs-digital"
    assert res.source_system == "persal"
    assert res.scheme == "persal"

    # Upstream PERSAL HR master fields MUST NOT exist on the platform identity
    assert not hasattr(res, "_upstream_id_number")
    assert not hasattr(res, "_upstream_salary_notch")
    assert not hasattr(res, "_upstream_pension_fund")


@pytest.mark.asyncio
async def test_external_hr_systems_endpoint(admin_headers):
    """GET /admin/hr/external/systems documents the active integrations and POPIA data minimization policy."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/hr/external/systems", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "connected"
        assert "surname" in data["popia_data_minimization_policy"]["retained_fields"]
        assert "position" in data["popia_data_minimization_policy"]["retained_fields"]
        assert "employee_code" in data["popia_data_minimization_policy"]["retained_fields"]
        assert "salary_notch_band" in data["popia_data_minimization_policy"]["excluded_hr_master_data"]

        systems = {s["id"]: s for s in data["systems"]}
        assert "sita-sap-hcm" in systems
        assert "persal" in systems
        assert systems["sita-sap-hcm"]["status"] == "ACTIVE_INTEGRATED"
        assert systems["persal"]["status"] == "ACTIVE_INTEGRATED"


@pytest.mark.asyncio
async def test_external_hr_lookup_sita(admin_headers):
    """GET /admin/hr/external/lookup?system=sita queries SITA Employee System."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/hr/external/lookup?system=sita&code=SIT-00204", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["system"] == "sita"
        assert data["total"] == 1
        item = data["items"][0]
        assert item["employee_code"] == "SIT-00204"
        assert item["surname"] == "Govender"
        assert "National Security Estate" in item["position"]
        # Sensitive master fields are stripped
        assert "_upstream_id_number" not in item
        assert "_upstream_salary_band" not in item


@pytest.mark.asyncio
async def test_external_hr_lookup_persal(admin_headers):
    """GET /admin/hr/external/lookup?system=persal queries National Treasury PERSAL."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/admin/hr/external/lookup?system=persal&code=80512891", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["system"] == "persal"
        assert data["total"] == 1
        item = data["items"][0]
        assert item["employee_code"] == "80512891"
        assert item["surname"] == "Dlamini"
        assert "DHA Branch Admin" in item["position"]
        assert item["department_id"] == "home-affairs-digital"
        assert item["branch_id"] == "dha-immigration"


@pytest.mark.asyncio
async def test_external_hr_import(admin_headers):
    """POST /admin/hr/external/import saves only minimal identity without HR master data."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    app.dependency_overrides[get_session] = lambda: mock_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {"system": "persal", "employee_code": "80621430"}
            resp = await ac.post("/admin/hr/external/import", json=payload, headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "imported"
            assert data["employee_code"] == "80621430"
            assert data["surname"] == "Botha"
            assert "Principal AppSec" in data["position"]
            assert data["department_id"] == "home-affairs-digital"
            assert data["branch_id"] == "dha-immigration"
    finally:
        app.dependency_overrides.pop(get_session, None)
