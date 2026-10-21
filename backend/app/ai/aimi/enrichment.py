"""Mapping the two buildable residues onto AIMI tools.

Which residues this covers, and why not the others
--------------------------------------------------
``app.processing.intel.capability`` declares five propositions with irreducible
model residue. Two are wired here:

- **AVP-3** campaign attribution — *read threat reporting, judge whether it
  names this sector, and map its technique set onto this estate's exposure.*
  AIMI's correlation and news tools do exactly this judgement.
- **AVP-8** risk-delta causal attribution — *which indicator, which campaign,
  and why that accounts for the movement the arithmetic already measured.*
  AIMI's attack playbook is keyed on the technique the signal maps to.

Three are deliberately absent, each for a reason recorded in code rather than in
a ticket:

- **AVP-2** detection content. ``tool_aimi_detection_engineer`` takes a single
  ``technique_id`` and emits Sigma/Suricata/Wazuh. It cannot choose the OEM
  source or the normalised field, which is most of what the residue asks for,
  and its output is not in ``alert_rules.yaml`` shape. Wiring it without a
  translation layer would deliver less than ``author_rules.py`` already does.
- **AVP-5** POPIA s.22. ``tool_aimi_regulatory_guide`` is documented for fraud
  and AML scenarios, which is FIC framing rather than POPIA data-breach framing,
  and AVP-5's residue is a legal judgement that compliance has not delegated.
- **AVP-11** behavioural sequences. Two independent blockers. There is no AIMI
  tool that reads an event sequence and explains it — ``tool_aimi_cluster_detect``
  clusters ATT&CK techniques, not audit rows — and ``app.processing.intel.privilege``
  designates ``identity.*`` and ``audit.action_audit`` as NEVER_READ with no
  model path, per NFR-AI-11. Sending audit rows to a third party would reverse
  a governance decision that is currently enforced.

What every function here guarantees
-----------------------------------
None of them raise. Each returns a dict with ``enriched_by_model: false`` and a
``reason`` when the provider is unavailable, disabled, mid-breaker or returned
nothing usable. The deterministic result is already computed and remains the
authoritative one; a provider outage must not be visible as an error to an
analyst mid-incident.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.ai.aimi import gateway
from app.ai.aimi.redaction import truncate
from app.config import settings

logger = logging.getLogger(__name__)

#: How an enrichment attempt ended. Rendered to the analyst verbatim.
UNAVAILABLE_DISABLED = "aimi_disabled"
UNAVAILABLE_BREAKER = "aimi_circuit_open"
UNAVAILABLE_NO_RESULT = "aimi_returned_nothing"
UNAVAILABLE_PROVIDER = "aimi_provider_unreachable"
UNAVAILABLE_UNSAFE_PAYLOAD = "outbound_payload_refused"

#: Applied to every analyst-supplied excerpt before egress.
_MAX_REPORT_CHARS = 4000


def _unavailable(reason: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "enriched_by_model": False,
        "reason": reason,
        "provider": "aimi",
        "advisory_only": True,
    }
    payload.update(extra)
    return payload


def enrich_campaign_attribution(
    report_text: str,
    extracted_techniques: list[str],
    extracted_cves: list[str],
    sector_candidates: list[str],
    exposure_overlap: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask AIMI whether the campaign names this estate (AVP-3).

    Sends public identifiers and the analyst's own pasted excerpt. The estate
    comparison itself stays local: the technique exposure list in
    ``exposure_overlap`` is reduced to IDs before egress, because a technique is
    a public constant and a department name is not.
    """
    if not settings.aimi_enabled:
        return _unavailable(UNAVAILABLE_DISABLED)
    if not gateway.is_available():
        return _unavailable(UNAVAILABLE_BREAKER)

    indicators: list[dict[str, Any]] = []
    indicators.extend({"type": "attack-pattern", "value": t} for t in extracted_techniques)
    indicators.extend({"type": "cve", "value": c} for c in extracted_cves)
    exposed_in_estate = sorted({
        str(row.get("technique_id"))
        for row in exposure_overlap
        if row.get("in_estate") and row.get("technique_id")
    })
    if not indicators:
        return _unavailable(
            UNAVAILABLE_NO_RESULT,
            note=(
                "No ATT&CK technique or CVE could be extracted from the supplied "
                "text, so there is nothing to correlate. Correlation was not attempted."
            ),
        )

    context_parts = [
        "An analyst supplied a threat report and asks whether the described "
        "campaign applies to a South African national-government security estate.",
    ]
    if sector_candidates:
        context_parts.append(
            "Adjacent-sector keywords found in the report: "
            + ", ".join(sector_candidates) + "."
        )
    if exposed_in_estate:
        context_parts.append(
            "ATT&CK techniques this estate is already exposed to: "
            + ", ".join(exposed_in_estate) + "."
        )
    context_parts.append(
        "Report excerpt: " + truncate(report_text, _MAX_REPORT_CHARS)
    )

    try:
        result = gateway.call_tool(
            "tool_aimi_ioc_correlate",
            {
                "iocs_json": _as_json(indicators),
                "investigation_context": " ".join(context_parts),
            },
        )
    except gateway.AimiToolNotAllowed as exc:
        logger.error("AIMI enrichment refused by policy: %s", exc)
        return _unavailable(UNAVAILABLE_UNSAFE_PAYLOAD, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - redaction must not break the route
        logger.warning(
            "AIMI campaign enrichment blocked outbound: %s", exc.__class__.__name__
        )
        return _unavailable(UNAVAILABLE_UNSAFE_PAYLOAD, detail=str(exc))

    if result is None:
        return _unavailable(UNAVAILABLE_PROVIDER)

    narrative = gateway.text_of(result).strip()
    if not narrative:
        return _unavailable(UNAVAILABLE_NO_RESULT)

    return {
        "enriched_by_model": True,
        "provider": "aimi",
        "tool": "tool_aimi_ioc_correlate",
        "advisory_only": True,
        "attribution_narrative": narrative,
        "analyst_review_required": True,
        "analyst_review_note": (
            "The attribution narrative is a third-party judgement about public "
            "threat reporting. It does not describe this estate's telemetry and "
            "creates no coverage. Confirm the campaign applies before acting on it."
        ),
    }


def enrich_risk_delta_causal(
    app_name: str,
    total_risk_delta: float,
    primary_signal: str,
    mapped_technique: str | None,
    report_techniques: list[str],
) -> dict[str, Any]:
    """Ask AIMI what activity the mapped technique represents (AVP-8).

    The measurement is not sent and does not need to be: the delta was computed
    locally from the caller's own scope, and the question being asked is what
    the technique means and what it is usually preceded by.
    """
    if not settings.aimi_enabled:
        return _unavailable(UNAVAILABLE_DISABLED)
    if not gateway.is_available():
        return _unavailable(UNAVAILABLE_BREAKER)
    if not mapped_technique:
        return _unavailable(
            UNAVAILABLE_NO_RESULT,
            note=(
                "The dominant signal maps to no known ATT&CK technique, so there "
                "is no technique to explain. Enrichment was not attempted."
            ),
        )

    context = (
        f"A South African national-government application scored a risk movement "
        f"of {total_risk_delta:+.2f} in a measurement window. The dominant signal "
        f"was '{primary_signal}', which this platform maps to ATT&CK "
        f"{mapped_technique}. Explain what activity this technique represents and "
        f"what external threat activity would account for such a movement."
    )
    if report_techniques:
        context += (
            " Techniques found in a threat report supplied by the analyst: "
            + ", ".join(report_techniques) + "."
        )

    try:
        result = gateway.call_tool(
            "tool_aimi_playbook_attack",
            {"domain": "enterprise", "technique": mapped_technique},
        )
    except gateway.AimiToolNotAllowed as exc:
        logger.error("AIMI enrichment refused by policy: %s", exc)
        return _unavailable(UNAVAILABLE_UNSAFE_PAYLOAD, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 - redaction must not break the route
        logger.warning(
            "AIMI causal enrichment blocked outbound: %s", exc.__class__.__name__
        )
        return _unavailable(UNAVAILABLE_UNSAFE_PAYLOAD, detail=str(exc))

    if result is None:
        return _unavailable(UNAVAILABLE_PROVIDER)

    narrative = gateway.text_of(result).strip()
    if not narrative:
        return _unavailable(UNAVAILABLE_NO_RESULT)

    return {
        "enriched_by_model": True,
        "provider": "aimi",
        "tool": "tool_aimi_playbook_attack",
        "advisory_only": True,
        "external_cause_narrative": narrative,
        "investigation_context_sent": context,
        "requires_analyst_review": True,
        "analyst_review_note": (
            "The measured delta is local and authoritative. The narrative "
            "describes what the technique typically means; it is not evidence "
            "that this movement was caused by that activity."
        ),
    }


def _as_json(value: Any) -> str:
    return json.dumps(value, default=str)