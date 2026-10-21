"""Gate 1: Report-Type RBAC & Report Catalog for AI Report Generation.

Implements Gate 1 of the G2 specification:
Validates whether the caller's role set grants authorization to request
a specific AI report type. Default-deny on all unknown or unauthorized roles.
"""
from typing import Any

REPORT_CATALOGUE: dict[str, dict[str, Any]] = {
    "executive_summary": {
        "title": "Executive Security Posture Briefing",
        "description": "High-level strategic briefing on cybersecurity health, exposure trends, and estate-wide risk posture.",
        "allowed_roles": {"exec", "admin", "operator"},
        "claim_class": "STRATEGIC_AGGREGATE",
        "cadence": "Monthly / On-Demand",
        "icon": "shield-alert",
    },
    "threat_intel_brief": {
        "title": "SOC Threat Intelligence & Alert Triage Brief",
        "description": "Operational analysis of active security alerts, correlated attack vectors, and intrusion detection telemetry.",
        "allowed_roles": {"soc", "appsec", "province-soc-lead", "admin", "operator"},
        "claim_class": "OPERATIONAL_TELEMETRY",
        "cadence": "Weekly / Real-Time",
        "icon": "radar",
    },
    "vulnerability_posture": {
        "title": "Application Security & Vulnerability Analysis",
        "description": "Technical synthesis of SAST and DAST findings, OWASP Top 10 breakdown, and remediation prioritization.",
        "allowed_roles": {"appsec", "local-appsec", "admin", "operator"},
        "claim_class": "TECHNICAL_VULNERABILITY",
        "cadence": "Sprint / Bi-Weekly",
        "icon": "bug",
    },
    "compliance_status": {
        "title": "Regulatory & Security Framework Compliance",
        "description": "Comprehensive review of adherence to POPIA, ISO 27001, NIST, and Minimum Interoperability Standards (MIOS).",
        "allowed_roles": {"compliance", "admin", "operator"},
        "claim_class": "REGULATORY_COMPLIANCE",
        "cadence": "Quarterly / On-Demand",
        "icon": "file-check",
    },
    "incident_summary": {
        "title": "Security Incident & Dispatch Investigation Report",
        "description": "Post-incident review of triggered high-severity alerts, response times, and containment verification.",
        "allowed_roles": {"soc", "province-soc-lead", "admin", "operator"},
        "claim_class": "INCIDENT_AUDIT",
        "cadence": "Post-Incident",
        "icon": "alert-triangle",
    },
    "popia_impact_assessment": {
        "title": "POPIA Data Protection & Privacy Impact Assessment",
        "description": "Section 22 breach exposure analysis, personal information vulnerability risks, and data subject protection metrics.",
        "allowed_roles": {"compliance", "admin", "operator"},
        "claim_class": "PRIVACY_IMPACT",
        "cadence": "On-Demand / Milestone",
        "icon": "lock",
    },
    "ag_audit_readiness": {
        "title": "Auditor-General (AGSA) Information Systems Audit Brief",
        "description": "Formal governance posture, cryptographically verifiable attestation readiness, and internal control status.",
        "allowed_roles": {"compliance", "admin", "operator"},
        "claim_class": "AUDIT_ATTESTATION",
        "cadence": "Annual / Half-Yearly",
        "icon": "clipboard-check",
    },
}


def can_access_report(user_roles: list[str], report_type: str) -> bool:
    """Gate 1 capability check: returns True if caller holds an authorized role."""
    report_info = REPORT_CATALOGUE.get(report_type)
    if not report_info:
        return False
    allowed_roles = report_info["allowed_roles"]
    return any(role in allowed_roles for role in user_roles)


def get_available_reports(user_roles: list[str]) -> list[dict[str, Any]]:
    """Return catalogue metadata for reports accessible to the given role set."""
    classifications = {
        "executive_summary": "RESTRICTED // SITA INTERNAL",
        "threat_intel_brief": "CONFIDENTIAL // SOC OPERATIONS",
        "vulnerability_posture": "INTERNAL // DEVSECOPS USE ONLY",
        "compliance_status": "OFFICIAL // COMPLIANCE DIVISION",
        "incident_summary": "CONFIDENTIAL // INCIDENT RESPONSE",
        "popia_impact_assessment": "OFFICIAL // PRIVACY REGULATOR",
        "ag_audit_readiness": "RESTRICTED // AUDIT ATTESTATION",
    }
    audiences = {
        "executive_summary": "Ministers, DGs, Board Members, CISOs",
        "threat_intel_brief": "SOC Analysts, Incident Responders, Threat Hunters",
        "vulnerability_posture": "AppSec Engineers, DevSecOps, System Architects",
        "compliance_status": "Compliance Officers, Information Regulators, Legal Counsel",
        "incident_summary": "Incident Commanders, SOC Leads, Forensic Analysts",
        "popia_impact_assessment": "Information Regulators, Legal Counsel, DPOs",
        "ag_audit_readiness": "Auditor-General, Audit Committees, IT Risk Leads",
    }
    available = []
    for report_id, meta in REPORT_CATALOGUE.items():
        if can_access_report(user_roles, report_id):
            available.append({
                "report_type": report_id,
                "name": meta["title"],
                "title": meta["title"],
                "description": meta["description"],
                "target_audience": audiences.get(report_id, meta["description"]),
                "classification": classifications.get(report_id, "RESTRICTED // SITA INTERNAL"),
                "claim_class": meta["claim_class"],
                "cadence": meta["cadence"],
                "icon": meta["icon"],
            })
    return available
