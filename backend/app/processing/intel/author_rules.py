"""AVP-2: Authoring alerting rules for received telemetry.

AI Residue Requirement:
-----------------------
Given an attacker technique present in received telemetry but lacking alerting,
decide which OEM source and normalised field evidences it, choose the predicate
and threshold, and emit a rule in the platform's own ``alert_rules.yaml`` shape.

Scope & Constraints:
--------------------
- Telemetry sources: ``appscan``, ``imperva_waf``, ``imperva_dam``, ``apisec``.
- Fields evaluated: ``severity``, ``source``, ``category``, ``attack_type``.
- Output: A reviewable proposal dictionary and unified ``git diff`` against
  ``backend/app/processing/alert_rules.yaml``.
- Advisory only: Rules are NEVER automatically merged. Human operator review is mandatory.
- Sigma, Suricata, Wazuh, and YARA rules are explicitly out of scope (they belong to external SIEM/IDS).
"""
from __future__ import annotations

import difflib
import os
import re
from pathlib import Path
from typing import Any

import yaml

from app.processing.intel.attack import hunt_source_for, techniques_for_cwe

ALERT_RULES_PATH = (
    Path(__file__).resolve().parent.parent / "alert_rules.yaml"
).resolve()

#: Known mappings from ATT&CK technique to platform log sources and predicates
TECHNIQUE_RULE_ARCHETYPES: dict[str, dict[str, Any]] = {
    "T1190": {
        "name": "Exploit Public-Facing Application Telemetry",
        "severity": "high",
        "source": "imperva_waf",
        "category": "Injection",
        "attack_type": "SQL Injection / RCE",
        "throttle": {"window_minutes": 15, "max_alerts": 3},
        "channels": ["teams", "pagerduty"],
        "condition_type": "record",
        "rationale": "Directly correlates external ingress WAF blocks and AppScan injection findings targeting exposed web applications.",
    },
    "T1059": {
        "name": "Command and Scripting Interpreter Execution",
        "severity": "high",
        "source": "imperva_waf",
        "category": "Remote Code Execution",
        "attack_type": "Command Injection",
        "throttle": {"window_minutes": 10, "max_alerts": 2},
        "channels": ["teams", "pagerduty"],
        "condition_type": "record",
        "rationale": "Flags OS command injection patterns observed across HTTP parameters or database stored procedure calls.",
    },
    "T1003": {
        "name": "OS Credential Dumping & Unauthorized Database Exfiltration",
        "severity": "critical",
        "source": "imperva_dam",
        "category": "Credential Access",
        "attack_type": "Mass Table Scan / Schema Dump",
        "throttle": {"window_minutes": 5, "max_alerts": 1},
        "channels": ["email", "teams", "pagerduty"],
        "condition_type": "record",
        "rationale": "Evidenced by Imperva DAM critical audit events monitoring unauthorized mass reads on identity/credential tables.",
    },
    "T1505": {
        "name": "Server Software Component Webshell Activity",
        "severity": "critical",
        "source": "appscan",
        "category": "Security Misconfiguration",
        "attack_type": "Webshell / Backdoor",
        "throttle": {"window_minutes": 30, "max_alerts": 2},
        "channels": ["teams", "pagerduty"],
        "condition_type": "record",
        "rationale": "AppScan finding detection for backdoor files, webshell persistence artifacts, or unauthorized upload endpoints.",
    },
    "T1078": {
        "name": "Valid Accounts - Compromised Credential Telemetry",
        "severity": "high",
        "source": "apisec",
        "category": "Broken Authentication",
        "attack_type": "Token Replay / Credential Stuffing",
        "throttle": {"window_minutes": 15, "max_alerts": 3},
        "channels": ["teams", "email"],
        "condition_type": "record",
        "rationale": "Correlates API security alerts detecting anomalous access volume or token reuse under valid user identities.",
    },
    "T1486": {
        "name": "Data Encrypted for Impact - Ransomware Payload Telemetry",
        "severity": "critical",
        "source": "imperva_dam",
        "category": "Mass Update / Destruction",
        "attack_type": "Database Encryption / Dropped Tables",
        "throttle": {"window_minutes": 5, "max_alerts": 1},
        "channels": ["email", "teams", "pagerduty"],
        "condition_type": "record",
        "rationale": "Monitors destructive DDL/DML statements executing in rapid succession across citizen registry databases.",
    },
}


def _load_current_rules_text() -> str:
    if ALERT_RULES_PATH.exists():
        with open(ALERT_RULES_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    return "rules: []\n"


def author_rule_for_technique(
    technique_id: str,
    technique_name: str | None = None,
    custom_severity: str | None = None,
    target_source: str | None = None,
) -> dict[str, Any]:
    """Author a reviewable alert rule proposal in platform vocabulary (AVP-2)."""
    tech_id_clean = technique_id.upper().strip()
    
    # Retrieve archetype or synthesize from technique characteristics
    archetype = TECHNIQUE_RULE_ARCHETYPES.get(tech_id_clean)
    hunt_info = hunt_source_for(tech_id_clean) or {}

    rule_slug = re.sub(r"[^a-z0-9_]", "_", f"technique_{tech_id_clean.lower()}")
    name = (
        technique_name
        or (archetype["name"] if archetype else f"ATT&CK {tech_id_clean} Telemetry Detection")
    )
    severity = custom_severity or (archetype["severity"] if archetype else "high")
    source = target_source or (archetype["source"] if archetype else "appscan")
    
    rule_dict: dict[str, Any] = {
        "id": rule_slug,
        "name": name,
        "severity": severity,
        "condition": {
            "type": "record",
            "match": "all",
            "fields": {
                "severity": [severity] if severity == "critical" else ["critical", severity],
                "source": [source],
            },
        },
        "throttle": archetype["throttle"] if archetype else {"window_minutes": 30, "max_alerts": 3},
        "channels": archetype["channels"] if archetype else ["teams"],
    }

    if archetype and "attack_type" in archetype:
        rule_dict["condition"]["fields"]["category"] = [archetype["category"]]

    # Emit rule YAML
    rule_yaml = yaml.dump([rule_dict], sort_keys=False, default_flow_style=False)
    # Indent for alert_rules.yaml format (under rules:)
    indented_rule = "\n".join("  " + line if line.strip() else line for line in rule_yaml.strip().splitlines())

    current_rules_text = _load_current_rules_text()
    new_rules_text = current_rules_text.rstrip() + "\n\n" + indented_rule + "\n"

    # Generate unified git diff
    diff_lines = list(
        difflib.unified_diff(
            current_rules_text.splitlines(keepends=True),
            new_rules_text.splitlines(keepends=True),
            fromfile="a/backend/app/processing/alert_rules.yaml",
            tofile="b/backend/app/processing/alert_rules.yaml",
        )
    )
    git_diff = "".join(diff_lines)

    return {
        "avp": "AVP-2",
        "technique_id": tech_id_clean,
        "rule_id": rule_slug,
        "status": "PROPOSED_FOR_REVIEW",
        "advisory_only": True,
        "auto_merged": False,
        "rationale": (
            archetype.get("rationale") if archetype
            else f"Automated synthesis mapping MITRE ATT&CK technique {tech_id_clean} to normalized {source} telemetry fields."
        ),
        "rule_definition": rule_dict,
        "proposed_yaml": indented_rule,
        "git_diff": git_diff,
        "governance_note": (
            "Rule diff emitted as a proposal artefact for operator/transversal-admin review. "
            "Under SITA governance policy, alert_rules.yaml modifications require human code review approval."
        ),
    }
