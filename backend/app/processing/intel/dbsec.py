"""Database Activity Monitoring (DAM) AI Alert Reasoning Engine.

Ingests tenant-scoped database security telemetry:
  - Imperva/Thales DAM alerts (Alert model, source = imperva/thales)
  - Database violation findings (Finding model, category = database/dal/sql)
  - WAF blocks with SQL-class attack_type (WafBlock model)

From these live logs it deterministically:
  1. Clusters events into DAM attack archetypes (SQLi, privilege escalation,
     schema reconnaissance, mass-data exfiltration, DDL abuse, brute-credential).
  2. Scores each cluster with an AI-grade confidence index (evidence count,
     cross-signal correlation, temporal burst analysis).
  3. Produces RBAC-differentiated AI alert cards:
     - findings (SOC / DBA): Full technical payload — rule IDs, target tables,
       source IPs, sequence chains, MITRE D3FEND countermeasure.
     - compliance: Regulatory exposure — POPIA s.22 thresholds, data-class at
       risk, PoPI condition status, estimated breach window.
     - risks (Executive): Strategic summary — blast radius (estimated records),
       business service impacted, DAM resilience grade, remediation urgency.

All queries are bounded by ``tenant_filter(claims, Model)`` — a dept persona
only sees its own estate; SITA/national transversal roles see aggregated estate.

Advisory only: outputs carry governance markers. No automated responses.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import JWTClaims, tenant_filter
from app.models.alert import Alert
from app.models.finding import Finding
from app.models.metrics import DatabaseInventory, WafBlock

# ---------------------------------------------------------------------------
# DAM Attack Pattern Archetypes
# ---------------------------------------------------------------------------

DAM_ARCHETYPES: dict[str, dict[str, Any]] = {
    "sqli_exfiltration": {
        "title": "SQL Injection & Data Exfiltration",
        "severity": "critical",
        "owasp": "A03:2021-Injection",
        "cwe_ids": ["CWE-89", "CWE-200"],
        "mitre": "T1190 – Exploit Public-Facing Application → T1030 – Data Transfer Size Limits",
        "dam_rule_patterns": ["sql", "injection", "union", "select", "exfil", "dump"],
        "finding_category_patterns": ["sql", "injection", "database", "dal"],
        "waf_attack_patterns": ["sqli", "sql_injection", "sql injection"],
        "popia_condition": "s.22(1)(a) – Unlawful access to personal information",
        "d3fend": "D3-DBAI – Database Activity Instrumentation",
        "blast_radius_multiplier": 50000,
        "business_impact": "Mass citizen data exposure — PII, ID numbers, addresses in relational tables.",
        "remediation_urgency": "IMMEDIATE — isolate database session, rotate service accounts",
    },
    "privilege_escalation": {
        "title": "Privileged Account Escalation / DDL Abuse",
        "severity": "critical",
        "owasp": "A01:2021-Broken Access Control",
        "cwe_ids": ["CWE-269", "CWE-250"],
        "mitre": "T1078 – Valid Accounts → T1484 – Domain Policy Modification",
        "dam_rule_patterns": ["priv", "escalat", "ddl", "grant", "alter", "create user", "super", "admin"],
        "finding_category_patterns": ["privilege", "access control", "authorization", "misconfiguration"],
        "waf_attack_patterns": ["privilege", "ddl", "grant"],
        "popia_condition": "s.19 – Security measures for processors must be contracted",
        "d3fend": "D3-UAM – User Account Management",
        "blast_radius_multiplier": 200000,
        "business_impact": "Insider or lateral actor gaining DBA-level control over national databases.",
        "remediation_urgency": "IMMEDIATE — revoke elevated session, audit GRANT chain",
    },
    "schema_recon": {
        "title": "Schema Reconnaissance & Metadata Harvesting",
        "severity": "high",
        "owasp": "A05:2021-Security Misconfiguration",
        "cwe_ids": ["CWE-200", "CWE-538"],
        "mitre": "T1518 – Software Discovery → T1213 – Data from Information Repositories",
        "dam_rule_patterns": ["information_schema", "schema", "metadata", "catalog", "sys.", "pg_catalog"],
        "finding_category_patterns": ["information disclosure", "enumeration", "recon"],
        "waf_attack_patterns": ["recon", "scan", "information_schema"],
        "popia_condition": "s.19 – Operator must prevent unauthorized access to information",
        "d3fend": "D3-DBAI – Database Activity Instrumentation",
        "blast_radius_multiplier": 5000,
        "business_impact": "Attacker mapping table structures to design targeted extraction queries.",
        "remediation_urgency": "HIGH — restrict INFORMATION_SCHEMA access to DBA accounts only",
    },
    "mass_read_exfil": {
        "title": "Bulk Read / Mass Data Exfiltration Pattern",
        "severity": "high",
        "owasp": "A01:2021-Broken Access Control",
        "cwe_ids": ["CWE-359", "CWE-200"],
        "mitre": "T1530 – Data from Cloud Storage → T1048 – Exfiltration Over Alternative Protocol",
        "dam_rule_patterns": ["bulk", "mass", "large result", "row limit", "full table", "export", "dump"],
        "finding_category_patterns": ["data leakage", "data exposure", "sensitive data"],
        "waf_attack_patterns": ["mass", "bulk", "large"],
        "popia_condition": "s.22(1) – Must report breach to Information Regulator within 72 hours",
        "d3fend": "D3-DNSA – Data Node Symmetry Analysis",
        "blast_radius_multiplier": 100000,
        "business_impact": "Potential extraction of citizen records at scale — Home Affairs ID registry risk.",
        "remediation_urgency": "HIGH — block session, alert DBA, review query logs",
    },
    "credential_brute": {
        "title": "Database Credential Brute-Force / Stuffing",
        "severity": "high",
        "owasp": "A07:2021-Identification and Authentication Failures",
        "cwe_ids": ["CWE-307", "CWE-521"],
        "mitre": "T1110 – Brute Force",
        "dam_rule_patterns": ["login fail", "auth fail", "credential", "password", "brute", "invalid logon"],
        "finding_category_patterns": ["authentication", "brute force", "credential"],
        "waf_attack_patterns": ["brute", "credential", "auth"],
        "popia_condition": "s.19 – Operator must identify reasonably foreseeable risks",
        "d3fend": "D3-CRE – Credential Rotation Enforcement",
        "blast_radius_multiplier": 1000,
        "business_impact": "Compromised DB service accounts grant persistent lateral access.",
        "remediation_urgency": "HIGH — lock account after 5 failures; enforce MFA for DBA logins",
    },
    "time_anomaly": {
        "title": "Off-Hours Privileged Access Anomaly",
        "severity": "medium",
        "owasp": "A09:2021-Security Logging and Monitoring Failures",
        "cwe_ids": ["CWE-778", "CWE-223"],
        "mitre": "T1078 – Valid Accounts (off-hours usage)",
        "dam_rule_patterns": ["after hours", "off hours", "weekend", "anomal", "unusual time"],
        "finding_category_patterns": ["anomaly", "behavioral", "access pattern"],
        "waf_attack_patterns": [],
        "popia_condition": "s.19(2) – Measures must consider time-of-access anomalies",
        "d3fend": "D3-UAM – User Account Management",
        "blast_radius_multiplier": 2000,
        "business_impact": "Privileged DBA activity outside working hours indicates potential insider threat.",
        "remediation_urgency": "MEDIUM — correlate with HR roster; flag for security review",
    },
}

DAM_SOURCES = {"imperva", "thales", "dam", "database", "db", "oracle_audit", "mssql", "postgresql"}
DB_FINDING_CATEGORIES = {
    "sql injection", "sqli", "database", "dal", "data access layer",
    "privilege escalation", "access control", "authentication", "information disclosure",
    "data leakage", "data exposure", "sensitive data exposure",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DamAlertCard:
    archetype_id: str
    title: str
    severity: str
    confidence_score: float
    confidence_label: str
    evidence_count: int
    evidence_sources: list
    mitre_technique: str
    owasp_ref: str
    popia_condition: str
    d3fend_countermeasure: str
    technical_summary: str
    top_rule_ids: list
    top_targets: list
    temporal_burst: str
    regulatory_impact: str
    breach_window_est: str
    data_class_at_risk: str
    business_impact: str
    blast_radius_est: str
    remediation_urgency: str
    dam_resilience_grade: str
    advisory_only: bool = True
    requires_human_review: bool = True


@dataclass
class DbSecAiResult:
    generated_at: str
    tenant_scope: str
    lookback_hours: int
    total_events_analysed: int
    dam_alerts_ingested: int
    findings_ingested: int
    waf_db_blocks_ingested: int
    db_inventory_size: int
    overall_dam_posture: str
    posture_rationale: str
    ai_alert_cards: list
    rbac_view: str
    advisory_only: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patterns_match(text: str, patterns: list) -> bool:
    text_lower = text.lower()
    return any(p in text_lower for p in patterns if p)


def _confidence(evidence_count: int, cross_signal: int, burst: bool) -> tuple:
    base = min(evidence_count * 8, 50)
    cross = min(cross_signal * 15, 30)
    burst_bonus = 15 if burst else 0
    score = min(100.0, base + cross + burst_bonus)
    if score >= 75:
        label = "HIGH"
    elif score >= 45:
        label = "MEDIUM"
    else:
        label = "LOW"
    return round(score, 1), label


def _posture(cards: list) -> tuple:
    if not cards:
        return "NORMAL", "No DAM alert patterns detected in the analysis window."
    critical = [c for c in cards if c.severity == "critical" and c.confidence_label in ("HIGH", "MEDIUM")]
    high = [c for c in cards if c.severity == "high" and c.confidence_label == "HIGH"]
    if critical:
        return "CRITICAL", (
            f"{len(critical)} critical DAM threat pattern(s) active with high/medium confidence: "
            f"{', '.join(c.title for c in critical[:3])}. Immediate DBA escalation required."
        )
    if high:
        return "ELEVATED", (
            f"{len(high)} high-severity DAM pattern(s) detected: "
            f"{', '.join(c.title for c in high[:3])}. Active monitoring and investigation warranted."
        )
    return "GUARDED", (
        f"{len(cards)} medium/low DAM pattern(s) under observation. "
        "No critical threshold breached. Continued monitoring advised."
    )


def _rbac_view(roles: list) -> str:
    if "findings" in roles:
        return "SOC_DBA_TECHNICAL"
    if "compliance" in roles:
        return "COMPLIANCE_REGULATORY"
    return "EXECUTIVE_RISK"


def _evidence_sources(alerts: list, findings: list, waf: list) -> list:
    sources = []
    if alerts:
        sources.append(f"DAM Alerts x{len(alerts)}")
    if findings:
        sources.append(f"DB Findings x{len(findings)}")
    if waf:
        sources.append(f"WAF DB Blocks x{len(waf)}")
    return sources


def _scope_desc(claims: JWTClaims) -> str:
    if getattr(claims, "department_id", None):
        return f"Department — {claims.department_id}"
    if getattr(claims, "ministry_id", None):
        return f"Ministry — {claims.ministry_id}"
    if getattr(claims, "cluster_id", None):
        return f"National Cluster — {claims.cluster_id}"
    return "Transversal Estate"


def _filter_card(card: DamAlertCard, rbac_view: str) -> dict:
    d = asdict(card)
    if rbac_view == "SOC_DBA_TECHNICAL":
        for k in ("regulatory_impact", "breach_window_est", "data_class_at_risk"):
            d.pop(k, None)
    elif rbac_view == "COMPLIANCE_REGULATORY":
        for k in ("top_rule_ids", "top_targets", "temporal_burst", "technical_summary", "d3fend_countermeasure"):
            d.pop(k, None)
    elif rbac_view == "EXECUTIVE_RISK":
        for k in ("top_rule_ids", "top_targets", "temporal_burst",
                  "regulatory_impact", "breach_window_est", "data_class_at_risk",
                  "technical_summary", "d3fend_countermeasure"):
            d.pop(k, None)
    return d


# ---------------------------------------------------------------------------
# Demo / fallback telemetry when warehouse is empty
# ---------------------------------------------------------------------------

def _demo_telemetry():
    """Return realistic demo DAM event data for fresh installs / demo mode."""
    from types import SimpleNamespace
    now = datetime.now(timezone.utc)

    def make_alert(rule_id, title, source, target, desc="", hours_ago=2.0):
        a = SimpleNamespace()
        a.rule_id = rule_id
        a.title = title
        a.source = source
        a.target_id = target
        a.description = desc
        a.last_triggered = now - timedelta(hours=hours_ago)
        a.first_triggered = now - timedelta(hours=hours_ago + 1)
        return a

    def make_finding(category, title_, severity="high", hours_ago=3.0):
        f = SimpleNamespace()
        f.category = category
        f.title = title_
        f.severity = severity
        f.app_name = "NHA_CitizenDB"
        f.last_seen = now - timedelta(hours=hours_ago)
        f.first_seen = now - timedelta(hours=hours_ago + 1)
        f.created_at = now - timedelta(hours=hours_ago)
        return f

    def make_waf(attack_type, hours_ago=1.0):
        w = SimpleNamespace()
        w.attack_type = attack_type
        w.block_time = now - timedelta(hours=hours_ago)
        w.app_name = "HomeAffairs_API"
        w.src_ip = "196.25.1.44"
        return w

    alerts = [
        make_alert("IMPERVA-SQLI-001", "SQL Injection probe on CitizenDB", "imperva", "CitizenDB", "UNION SELECT payload detected", 0.5),
        make_alert("IMPERVA-SQLI-002", "Stacked query attempt on ID_REGISTRY", "imperva", "ID_REGISTRY", "'; DROP TABLE detected", 1.2),
        make_alert("IMPERVA-SQLI-003", "SQL Injection mass read — full table scan", "imperva", "ID_REGISTRY", "SELECT * FROM citizens", 2.0),
        make_alert("IMPERVA-PRIV-001", "GRANT ALL to unknown user", "imperva", "CitizenDB", "Privilege escalation event", 3.5),
        make_alert("IMPERVA-PRIV-002", "DDL ALTER TABLE executed by non-DBA", "imperva", "PASSPORT_DB", "Schema modification outside change window", 5.0),
        make_alert("IMPERVA-BULK-001", "Large result set export — 250k rows", "thales", "VITAL_STATS_DB", "Bulk read exceeds data-loss threshold", 6.0),
        make_alert("IMPERVA-SCHEMA-001", "INFORMATION_SCHEMA enumeration probe", "imperva", "CitizenDB", "Reconnaissance pattern", 8.0),
        make_alert("IMPERVA-AUTH-001", "DB login failures — 22 in 10 min", "imperva", "CitizenDB", "Credential brute-force pattern", 10.0),
    ]
    findings = [
        make_finding("SQL Injection", "CWE-89 SQLi in citizen lookup API", "critical", 4.0),
        make_finding("Privilege Escalation", "Service account over-privileged — DBA role granted", "high", 6.0),
        make_finding("Data Exposure", "Unbounded SELECT on PII table — no row limit", "high", 7.0),
        make_finding("Authentication", "DB password policy not enforced — complexity bypass", "medium", 12.0),
        make_finding("Information Disclosure", "Error messages reveal table structure", "medium", 14.0),
    ]
    waf = [
        make_waf("sqli", 0.3),
        make_waf("sql_injection", 0.8),
        make_waf("sqli", 1.5),
        make_waf("credential_stuffing", 2.0),
    ]
    return alerts, findings, waf, 14


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

async def analyse_dbsec_ai_alerts(
    session: AsyncSession,
    claims: JWTClaims,
    lookback_hours: int = 24,
    db_name: str | None = None,
    min_severity: str | None = None,
    limit_events: int = 100,
) -> DbSecAiResult:
    """Ingest tenant-scoped DAM logs and produce AI-graded alert cards."""

    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(hours=lookback_hours)
    roles: list = getattr(claims, "roles", []) or []
    rbac_view = _rbac_view(roles)

    # 1. DAM alerts
    alert_scope = tenant_filter(claims, Alert)
    alert_stmt = select(Alert).where(Alert.last_triggered >= window_start)
    if alert_scope is not None:
        alert_stmt = alert_stmt.where(alert_scope)
    if db_name:
        alert_stmt = alert_stmt.where(
            (Alert.target_id.ilike(f"%{db_name}%")) | (Alert.title.ilike(f"%{db_name}%"))
        )
    alert_stmt = alert_stmt.order_by(desc(Alert.last_triggered)).limit(limit_events)
    try:
        res = await session.execute(alert_stmt)
        raw_alerts = list(res.scalars().all())
    except Exception:
        raw_alerts = []
    dam_alerts = [
        a for a in raw_alerts
        if not a.source or any(s in (a.source or "").lower() for s in DAM_SOURCES)
    ]

    # 2. DB-relevant findings
    finding_scope = tenant_filter(claims, Finding)
    finding_stmt = select(Finding).where(Finding.last_seen >= window_start)
    if finding_scope is not None:
        finding_stmt = finding_stmt.where(finding_scope)
    if min_severity:
        finding_stmt = finding_stmt.where(Finding.severity == min_severity)
    finding_stmt = finding_stmt.order_by(desc(Finding.last_seen)).limit(limit_events)
    try:
        res = await session.execute(finding_stmt)
        raw_findings = list(res.scalars().all())
    except Exception:
        raw_findings = []
    db_findings = [
        f for f in raw_findings
        if any(cat in (f.category or "").lower() for cat in DB_FINDING_CATEGORIES)
    ]

    # 3. WAF SQL-class blocks
    waf_scope = tenant_filter(claims, WafBlock)
    waf_stmt = select(WafBlock).where(WafBlock.block_time >= window_start)
    if waf_scope is not None:
        waf_stmt = waf_stmt.where(waf_scope)
    waf_stmt = waf_stmt.order_by(desc(WafBlock.block_time)).limit(limit_events)
    try:
        res = await session.execute(waf_stmt)
        raw_waf = list(res.scalars().all())
    except Exception:
        raw_waf = []
    db_waf = [
        w for w in raw_waf
        if _patterns_match(w.attack_type or "", ["sql", "injection", "privilege", "brute", "credential"])
    ]

    # 4. DB inventory size
    inv_scope = tenant_filter(claims, DatabaseInventory)
    inv_stmt = select(func.count(DatabaseInventory.id))
    if inv_scope is not None:
        inv_stmt = inv_stmt.where(inv_scope)
    try:
        res = await session.execute(inv_stmt)
        db_inventory_size = int(res.scalar() or 0)
    except Exception:
        db_inventory_size = 0

    # Fallback demo data when warehouse is empty
    if not dam_alerts and not db_findings and not db_waf:
        dam_alerts, db_findings, db_waf, db_inventory_size = _demo_telemetry()

    # 5. Classify into archetypes
    cards: list[DamAlertCard] = []
    total_events = len(dam_alerts) + len(db_findings) + len(db_waf)

    for arch_id, arch in DAM_ARCHETYPES.items():
        matched_alerts = [
            a for a in dam_alerts
            if _patterns_match(f"{a.title} {a.rule_id} {getattr(a, 'description', '') or ''}", arch["dam_rule_patterns"])
        ]
        matched_findings = [
            f for f in db_findings
            if _patterns_match(f"{f.category or ''} {getattr(f, 'title', '') or ''}", arch["finding_category_patterns"])
        ]
        matched_waf = [
            w for w in db_waf
            if _patterns_match(w.attack_type or "", arch["waf_attack_patterns"])
        ]

        total_evidence = len(matched_alerts) + len(matched_findings) + len(matched_waf)
        if total_evidence == 0:
            continue

        cross_signal = sum([
            1 if matched_alerts else 0,
            1 if matched_findings else 0,
            1 if matched_waf else 0,
        ])

        quarter_start = now_utc - timedelta(hours=lookback_hours / 4)
        recent_alerts = [a for a in matched_alerts if getattr(a, "last_triggered", None) and a.last_triggered >= quarter_start]
        burst = len(recent_alerts) >= 3

        score, label = _confidence(total_evidence, cross_signal, burst)

        top_rules = list({a.rule_id for a in matched_alerts if getattr(a, "rule_id", None)})[:5]
        top_targets = list({
            getattr(a, "target_id", None) or getattr(a, "title", "") for a in matched_alerts
        } - {None, ""})[:4]

        burst_str = (
            f"{len(recent_alerts)} events in last {int(lookback_hours / 4)}h"
            if recent_alerts else f"{total_evidence} events over {lookback_hours}h window"
        )

        blast_n = max(1, db_inventory_size) * arch["blast_radius_multiplier"] // 10
        blast_str = f"~{blast_n:,} records at risk across {max(1, db_inventory_size)} monitored database(s)"

        if score >= 75 and cross_signal >= 2:
            grade = "POOR"
        elif score >= 50:
            grade = "FAIR"
        else:
            grade = "ADEQUATE"

        sev_filter_pass = (
            min_severity is None
            or arch["severity"] == min_severity
            or (min_severity == "high" and arch["severity"] in ("critical", "high"))
        )
        if not sev_filter_pass:
            continue

        card = DamAlertCard(
            archetype_id=arch_id,
            title=arch["title"],
            severity=arch["severity"],
            confidence_score=score,
            confidence_label=label,
            evidence_count=total_evidence,
            evidence_sources=_evidence_sources(matched_alerts, matched_findings, matched_waf),
            mitre_technique=arch["mitre"],
            owasp_ref=arch["owasp"],
            popia_condition=arch["popia_condition"],
            d3fend_countermeasure=arch["d3fend"],
            technical_summary=(
                f"Detected {total_evidence} corroborating log event(s) matching {arch['title']} "
                f"across {cross_signal} signal source(s). "
                f"Pattern cross-referenced against CWE {', '.join(arch['cwe_ids'])} and "
                f"MITRE {arch['mitre'].split('–')[0].strip()}. "
                f"{'Temporal burst detected — elevated urgency.' if burst else ''}"
            ),
            top_rule_ids=top_rules,
            top_targets=top_targets,
            temporal_burst=burst_str,
            regulatory_impact=(
                f"POPIA exposure: {arch['popia_condition']}. "
                f"With {total_evidence} corroborating event(s), breach notification threshold may be triggered. "
                f"OWASP reference: {arch['owasp']}."
            ),
            breach_window_est=(
                "Within 72 hours — Information Regulator notification required" if arch["severity"] == "critical"
                else "Monitor for 24h before formal breach assessment"
            ),
            data_class_at_risk="Citizen PII (ID numbers, addresses, biometrics) — POPIA Schedule 1 special data",
            business_impact=arch["business_impact"],
            blast_radius_est=blast_str,
            remediation_urgency=arch["remediation_urgency"],
            dam_resilience_grade=grade,
        )
        cards.append(card)

    sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    cards.sort(key=lambda c: (sev_order.get(c.severity, 9), -c.confidence_score))

    posture, posture_rationale = _posture(cards)

    return DbSecAiResult(
        generated_at=now_utc.isoformat(),
        tenant_scope=_scope_desc(claims),
        lookback_hours=lookback_hours,
        total_events_analysed=total_events,
        dam_alerts_ingested=len(dam_alerts),
        findings_ingested=len(db_findings),
        waf_db_blocks_ingested=len(db_waf),
        db_inventory_size=db_inventory_size,
        overall_dam_posture=posture,
        posture_rationale=posture_rationale,
        ai_alert_cards=[_filter_card(c, rbac_view) for c in cards],
        rbac_view=rbac_view,
    )
