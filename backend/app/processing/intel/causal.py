"""AVP-8 (b): Risk-delta causal attribution — external-cause enrichment.

AI Residue Requirement (per capability.py):
--------------------------------------------
Explain a computed risk movement in terms of external threat activity: which
indicator, which campaign, and why that accounts for the movement the arithmetic
already measured.

What this module provides
-------------------------
The deterministic part (signal decomposition) already lives in ``delta.py`` and
is exposed via ``GET /intel/risk/delta``. That endpoint documents the movement
and names the signals that drove it.

This module adds the *external-cause* enrichment layer:

1. ``enrich_delta_with_context`` — takes a delta payload from ``delta.app_delta``
   and cross-references its technique list against:
   a. The platform's own alert-coverage map (already in attack.py).
   b. A structured threat-report text, if supplied by the caller.
   The result is a structured narration stub: what moved, which signal drove it,
   which ATT&CK technique that corresponds to, and whether any threat report
   supplied by the caller mentions that technique.

Advisory only
-------------
The function returns a ``causal_hypothesis`` dict with a ``requires_analyst_review``
flag. Nothing is committed or dispatched. No external CTI feed is polled (that
would be an OTX/MISP call, out of scope for this consuming platform).

Gating note
-----------
The ``model_narration_requested`` field signals to a downstream AI layer that it
may produce a prose explanation from the structured output. The platform layer
is complete without that prose; the prose is a presentation convenience, not the
measurement.
"""
from __future__ import annotations

from typing import Any

from app.processing.intel.campaign import _extract_techniques


def enrich_delta_with_context(
    delta_payload: dict[str, Any],
    threat_report_text: str | None = None,
) -> dict[str, Any]:
    """Add external-cause context to a risk-delta payload (AVP-8 residue layer).

    Parameters
    ----------
    delta_payload:
        The output of ``delta.app_delta`` — contains ``app_name``,
        ``signals``, ``total_delta``, ``largest_mover_signal``, etc.
    threat_report_text:
        Optional raw text of an external threat report (CTI feed entry, blog
        post, MITRE ATT&CK advisory). If supplied, any techniques mentioned
        are cross-referenced against the signals in the delta.
    """
    app_name = delta_payload.get("app_name", "")
    largest_signal = delta_payload.get("largest_mover_signal", "")
    total_delta = delta_payload.get("total_delta", 0.0)

    # Map the dominant signal back to an ATT&CK technique if known
    # These signal-to-technique mappings are curated from the platform vocab
    SIGNAL_TO_TECHNIQUE: dict[str, str] = {
        "appscan": "T1190",           # Exploit Public-Facing Application
        "imperva_waf": "T1190",       # Exploit Public-Facing Application
        "imperva_dam": "T1003",       # OS Credential Dumping
        "apisec": "T1078",            # Valid Accounts
        "critical_findings": "T1190",
        "high_findings": "T1059",
        "waf_blocks": "T1190",
        "alerts": "T1059",
    }

    primary_technique = SIGNAL_TO_TECHNIQUE.get(largest_signal.lower(), None)

    # Extract techniques from threat report if provided
    report_techniques: list[str] = []
    if threat_report_text:
        report_techniques = _extract_techniques(threat_report_text)

    # Cross-reference
    technique_in_report = (
        primary_technique in report_techniques
        if primary_technique and report_techniques
        else None
    )

    causal_hypothesis: dict[str, Any] = {
        "app_name": app_name,
        "total_risk_delta": total_delta,
        "primary_signal": largest_signal,
        "mapped_technique": primary_technique,
        "technique_found_in_threat_report": technique_in_report,
        "techniques_in_supplied_report": report_techniques,
        "requires_analyst_review": True,
        "analyst_review_note": (
            "The arithmetic movement is measured. The external cause is a hypothesis: "
            "confirm whether the threat report supplied describes activity targeting "
            f"this estate and whether {primary_technique or 'the mapped technique'} "
            "accounts for the observed delta before this explanation is used in reporting."
        ),
        "model_narration_requested": bool(threat_report_text),
        "narration_stub": (
            f"The risk score for '{app_name}' changed by {total_delta:+.2f} in the "
            f"measurement window. The dominant contributing signal was '{largest_signal}'"
            + (
                f", which maps to ATT&CK {primary_technique}."
                if primary_technique
                else "."
            )
            + (
                f" The supplied threat report {'mentions' if technique_in_report else 'does not mention'} "
                f"this technique."
                if technique_in_report is not None
                else " No external threat report was supplied."
            )
        ),
    }

    return {
        "avp": "AVP-8",
        "advisory_only": True,
        "delta_summary": delta_payload,
        "causal_hypothesis": causal_hypothesis,
        "governance_note": (
            "Risk-delta causal attribution is a structured hypothesis, not a finding. "
            "Analyst confirmation is required before this explanation is included in "
            "executive or regulatory reporting."
        ),
    }
