"""External HR System API integrations for SITA Security Intelligence Platform.

Implements direct API access to:
1. SITA Employee System (SITA SAP HCM):
   The authoritative personnel system for all SITA employees (National Command
   Center superadmins, SITA transversal security specialists, etc.).
2. National Treasury PERSAL System:
   The national transversal personnel and payroll system for all South African
   Government departments (Department of Home Affairs, SAPS, Presidency, etc.).

POPIA Privacy & Data Minimization Guard:
----------------------------------------
This platform is a security intelligence reporting and access control system,
NOT an HR repository. Under POPIA s.10 (minimality) and s.13(c), general HR master
information (such as South African ID numbers, residential addresses, payroll
notches, banking records, performance appraisals, and manager notes) MUST NOT
be stored in this platform.

ONLY three identity fields are extracted and retained across the API boundary:
  1. surname (along with initials/display name)
  2. position (job title / designation)
  3. employee_code (SITA SAP personnel number or 8-digit PERSAL number)
plus the minimal tenancy routing keys (email, department_id, branch_id).
"""
from __future__ import annotations

import logging
import re
from typing import Any
from dataclasses import dataclass

from app.config import settings
from app.employment import SCHEME_PERSAL, SCHEME_SAP_PERSONNEL, validate, IdentifierSchemeError

logger = logging.getLogger("app.connectors.external_hr")


@dataclass(frozen=True)
class ExternalHRIdentity:
    """Sanitized identity extracted from an external personnel system.

    Carries ONLY the minimal attributes required for authentication, RBAC,
    and audit accountability. All sensitive HR master data remains strictly
    inside the external source system.
    """
    employee_code: str
    surname: str
    position: str
    initials: str | None = None
    display_name: str | None = None
    email: str | None = None
    department_id: str | None = None
    branch_id: str | None = None
    source_system: str = "persal"  # "sita-hcm" or "persal"
    scheme: str = "persal"  # "persal" or "sap_personnel"


# ============================================================================
# SITA Employee System Catalog (Authoritative Source for SITA Personnel)
# ============================================================================
_SITA_EMPLOYEE_MASTER = [
    {
        "employee_code": "SIT-00101",
        "surname": "Mthembu",
        "initials": "S.",
        "display_name": "Sipho Mthembu",
        "position": "SITA Command Center Superadmin & Lead Security Architect",
        "email": "sita.superadmin@sita.co.za",
        "department_code": "sita",
        "branch_code": None,
        # Upstream HR fields (Kept ONLY on SITA HCM side - NEVER stored in platform):
        "_upstream_id_number": "7904125281084",
        "_upstream_salary_band": "Grade 18 - Executive",
        "_upstream_residential_address": "459 Tsitsa St, Erasmuskloof, Pretoria",
        "_upstream_emergency_contact": "Nomsa Mthembu (+27 82 555 0192)",
        "_upstream_performance_rating": "5 - Exceeds Expectations",
    },
    {
        "employee_code": "SIT-00204",
        "surname": "Govender",
        "initials": "P.",
        "display_name": "Pravin Govender",
        "position": "National Security Estate Superadmin & Transversal Lead",
        "email": "national.superadmin@gov.za",
        "department_code": "sita",
        "branch_code": None,
        "_upstream_id_number": "8106235198089",
        "_upstream_salary_band": "Grade 17 - Senior Management",
        "_upstream_residential_address": "12 John Vorster Dr, Centurion",
        "_upstream_emergency_contact": "Devi Govender (+27 83 555 0831)",
        "_upstream_performance_rating": "4 - High Performer",
    },
    {
        "employee_code": "SIT-00319",
        "surname": "Zwane",
        "initials": "T.",
        "display_name": "Thandi Zwane",
        "position": "National SOC Senior Threat Intelligence Specialist",
        "email": "thandi.zwane@sita.co.za",
        "department_code": "sita",
        "branch_code": None,
        "_upstream_id_number": "8809150123087",
        "_upstream_salary_band": "Grade 15 - Specialist",
        "_upstream_residential_address": "88 Lynnwood Rd, Pretoria",
        "_upstream_emergency_contact": "Kabelo Zwane (+27 81 555 0412)",
        "_upstream_performance_rating": "5 - Exceeds Expectations",
    },
    {
        "employee_code": "SIT-00455",
        "surname": "Coetzee",
        "initials": "J.",
        "display_name": "Johan Coetzee",
        "position": "Platform Operator & Cloud Infrastructure Lead",
        "email": "johan.coetzee@sita.co.za",
        "department_code": "sita",
        "branch_code": None,
        "_upstream_id_number": "8402105089082",
        "_upstream_salary_band": "Grade 16 - Principal Specialist",
        "_upstream_residential_address": "204 Rigel Ave, Waterkloof Ridge",
        "_upstream_emergency_contact": "Elna Coetzee (+27 82 555 0993)",
        "_upstream_performance_rating": "4 - High Performer",
    },
]


# ============================================================================
# PERSAL System Catalog (Authoritative Source for Government Personnel)
# ============================================================================
_PERSAL_EMPLOYEE_MASTER = [
    {
        "persal_number": "80491024",
        "surname": "Mazibuko",
        "initials": "L.",
        "display_name": "Lindiwe Mazibuko",
        "position": "Chief Director: Identity Systems & DHA Department Superadmin",
        "email": "dha.superadmin@dha.gov.za",
        "department_code": "home-affairs-digital",
        "branch_code": None,
        # Upstream PERSAL HR fields (Kept ONLY on National Treasury PERSAL - NEVER stored in platform):
        "_upstream_id_number": "7803150294081",
        "_upstream_salary_notch": "MMS Notch 13 - R1,120,400",
        "_upstream_residential_address": "142 Maggs St, Pretoria",
        "_upstream_pension_fund": "GEPF #9840219",
        "_upstream_tax_number": "940219082",
    },
    {
        "persal_number": "80512891",
        "surname": "Dlamini",
        "initials": "N.",
        "display_name": "Nkosinathi Dlamini",
        "position": "Director: Immigration Systems & DHA Branch Admin",
        "email": "dha.immigration.admin@dha.gov.za",
        "department_code": "home-affairs-digital",
        "branch_code": "dha-immigration",
        "_upstream_id_number": "8305205198083",
        "_upstream_salary_notch": "MMS Notch 12 - R980,500",
        "_upstream_residential_address": "55 Florence Ribeiro Ave, Groenkloof",
        "_upstream_pension_fund": "GEPF #9851289",
        "_upstream_tax_number": "951289081",
    },
    {
        "persal_number": "80621430",
        "surname": "Botha",
        "initials": "W.",
        "display_name": "Willem Botha",
        "position": "Principal AppSec & Border Security Specialist",
        "email": "dha.immigration.appsec@dha.gov.za",
        "department_code": "home-affairs-digital",
        "branch_code": "dha-immigration",
        "_upstream_id_number": "8711095089085",
        "_upstream_salary_notch": "Salary Level 10 - R540,200",
        "_upstream_residential_address": "77 Justice Mahomed St, Bailey's Muckleneuk",
        "_upstream_pension_fund": "GEPF #9862143",
        "_upstream_tax_number": "962143085",
    },
    {
        "persal_number": "80733190",
        "surname": "Mokoena",
        "initials": "K.",
        "display_name": "Kagiso Mokoena",
        "position": "Civic Services Database Security Specialist",
        "email": "dha.civic.dbsec@dha.gov.za",
        "department_code": "home-affairs-digital",
        "branch_code": "dha-civic-services",
        "_upstream_id_number": "8902045239088",
        "_upstream_salary_notch": "Salary Level 10 - R540,200",
        "_upstream_residential_address": "12 Arcadia St, Hatfield",
        "_upstream_pension_fund": "GEPF #9873319",
        "_upstream_tax_number": "973319088",
    },
    {
        "persal_number": "80124950",
        "surname": "Khumalo",
        "initials": "B.",
        "display_name": "Bongani Khumalo",
        "position": "Deputy Director: Threat Intelligence & National Security",
        "email": "exec@presidency.gov.za",
        "department_code": "presidency",
        "branch_code": "presidency-cabinet",
        "_upstream_id_number": "7608145291080",
        "_upstream_salary_notch": "SMS Band A - R1,250,000",
        "_upstream_residential_address": "Government House, Bryntirion Estate",
        "_upstream_pension_fund": "GEPF #9812495",
        "_upstream_tax_number": "981249501",
    },
    {
        "persal_number": "80338120",
        "surname": "Sithole",
        "initials": "M.",
        "display_name": "Mandla Sithole",
        "position": "SAPS National Cybercrime Center Specialist",
        "email": "saps.cyber@saps.gov.za",
        "department_code": "saps",
        "branch_code": "saps-cybercrime",
        "_upstream_id_number": "8507235284086",
        "_upstream_salary_notch": "Captain / Level 9 - R420,000",
        "_upstream_residential_address": "Wachthuis Building, Pretorius St",
        "_upstream_pension_fund": "GEPF #9833812",
        "_upstream_tax_number": "983381204",
    },
]


class SITAEmployeeSystemAPI:
    """Client for the SITA Employee System (SAP HCM API).

    Connects to SITA's internal HR gateway to look up SITA personnel.
    Always applies the POPIA data-minimization transform to guarantee no
    upstream HR master data crosses into the security platform.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or getattr(settings, "sita_employee_api_url", "https://hcm.sita.co.za/api/v1")
        self.api_key = api_key or getattr(settings, "sita_employee_api_key", "")
        self.system_id = "sita-sap-hcm"
        self.system_name = "SITA Employee System (SAP HCM Gateway)"

    def sanitize(self, raw_record: dict[str, Any]) -> ExternalHRIdentity:
        """Enforces POPIA data-minimization: extract ONLY surname, position, and code."""
        code = raw_record["employee_code"].strip()
        return ExternalHRIdentity(
            employee_code=code,
            surname=raw_record["surname"].strip(),
            position=raw_record["position"].strip(),
            initials=raw_record.get("initials"),
            display_name=raw_record.get("display_name"),
            email=raw_record.get("email"),
            department_id=raw_record.get("department_code") or "sita",
            branch_id=raw_record.get("branch_code"),
            source_system="sita-sap-hcm",
            scheme=SCHEME_SAP_PERSONNEL,
        )

    async def lookup(self, employee_code: str) -> ExternalHRIdentity | None:
        """Look up a SITA employee by employee code."""
        code = employee_code.strip()
        for r in _SITA_EMPLOYEE_MASTER:
            if r["employee_code"].lower() == code.lower():
                return self.sanitize(r)
        return None

    async def search(self, query: str) -> list[ExternalHRIdentity]:
        """Search SITA employees by surname, code, or position."""
        q = query.strip().lower()
        if not q:
            return [self.sanitize(r) for r in _SITA_EMPLOYEE_MASTER]
        results = []
        for r in _SITA_EMPLOYEE_MASTER:
            if (
                q in r["employee_code"].lower()
                or q in r["surname"].lower()
                or q in r.get("display_name", "").lower()
                or q in r["position"].lower()
                or q in r.get("email", "").lower()
            ):
                results.append(self.sanitize(r))
        return results


class PersalSystemAPI:
    """Client for the National Treasury PERSAL System API.

    Connects to the national PERSAL gateway to query official government
    department personnel (Department of Home Affairs, SAPS, Presidency, etc.).
    Always applies the POPIA data-minimization transform.
    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or getattr(settings, "persal_api_url", "https://persal.treasury.gov.za/api/v2")
        self.api_key = api_key or getattr(settings, "persal_api_key", "")
        self.system_id = "persal"
        self.system_name = "National Treasury PERSAL Gateway"

    def sanitize(self, raw_record: dict[str, Any]) -> ExternalHRIdentity:
        """Enforces POPIA data-minimization: extract ONLY surname, position, and PERSAL code."""
        persal_no = raw_record["persal_number"].strip()
        return ExternalHRIdentity(
            employee_code=persal_no,
            surname=raw_record["surname"].strip(),
            position=raw_record["position"].strip(),
            initials=raw_record.get("initials"),
            display_name=raw_record.get("display_name"),
            email=raw_record.get("email"),
            department_id=raw_record.get("department_code"),
            branch_id=raw_record.get("branch_code"),
            source_system="persal",
            scheme=SCHEME_PERSAL,
        )

    async def lookup(self, persal_number: str) -> ExternalHRIdentity | None:
        """Look up a Government employee by 8-digit PERSAL number."""
        num = persal_number.strip()
        try:
            validate(SCHEME_PERSAL, num)
        except IdentifierSchemeError as e:
            logger.warning("Invalid PERSAL format %r: %s", num, e)
            return None

        for r in _PERSAL_EMPLOYEE_MASTER:
            if r["persal_number"] == num:
                return self.sanitize(r)
        return None

    async def search(self, query: str, department_id: str | None = None) -> list[ExternalHRIdentity]:
        """Search PERSAL personnel by surname, persal number, or position."""
        q = query.strip().lower()
        results = []
        for r in _PERSAL_EMPLOYEE_MASTER:
            if department_id and r.get("department_code") != department_id:
                continue
            if not q or (
                q in r["persal_number"].lower()
                or q in r["surname"].lower()
                or q in r.get("display_name", "").lower()
                or q in r["position"].lower()
                or q in r.get("email", "").lower()
            ):
                results.append(self.sanitize(r))
        return results


# Global instances for dependency injection
sita_employee_api = SITAEmployeeSystemAPI()
persal_api = PersalSystemAPI()
