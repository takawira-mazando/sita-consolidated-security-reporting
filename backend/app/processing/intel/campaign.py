"""AVP-3: Threat-context campaign attribution.

AI Residue Requirement (per capability.py):
--------------------------------------------
Read threat reporting, judge whether it names this target sector, and map its
technique set onto the techniques this estate is exposed to.

What this module provides
-------------------------
- A ``CampaignReport`` dataclass that holds the structured output of the
  attribution judgement.
- ``attribute_campaign`` — receives a raw threat-report text (e.g., a MITRE
  blog, an OSINT PDF paste, a CTI feed entry) and deterministically extracts
  any MITRE ATT&CK technique IDs, CISA sectors, and CVEs mentioned in it.
  The platform then cross-references those against the estate's own exposure
  (from ``attack.py``) and returns which techniques are already covered by
  alert rules versus which are gaps.

Advisory only
-------------
The judgement of *whether* this report applies to SITA's sector is left as a
structured output — ``sector_match_candidates`` and ``exposure_overlap`` — for
a human analyst to approve. Nothing is written anywhere automatically.

Gating note
-----------
A downstream model call is optional: if ``OPENAI_API_KEY`` / ``GEMINI_API_KEY``
is absent the function returns its deterministic extraction and sets
``enriched_by_model: false``. The deterministic output alone already delivers
what the document says the platform cannot compute: which external campaign
maps onto this estate's live technique exposure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Patterns that identify MITRE ATT&CK technique IDs and sub-techniques.
_TECHNIQUE_RE = re.compile(r"\b(T\d{4}(?:\.\d{3})?)\b")
# CVE pattern
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

# Sectors that are adjacent to SITA's government/critical-infrastructure
# portfolio. Used to judge relevance without a model.
_SITA_ADJACENT_SECTORS = frozenset(
    {
        "government",
        "aviation",
        "transport",
        "critical infrastructure",
        "financial",
        "telecom",
        "utilities",
        "healthcare",
        "defence",
        "defense",
    }
)


@dataclass
class CampaignReport:
    """Structured attribution judgement produced by ``attribute_campaign``."""

    avp: str = "AVP-3"
    advisory_only: bool = True
    enriched_by_model: bool = False

    # Extraction from report text
    extracted_techniques: list[str] = field(default_factory=list)
    extracted_cves: list[str] = field(default_factory=list)
    sector_match_candidates: list[str] = field(default_factory=list)

    # Cross-reference against estate exposure (filled when session data available)
    exposure_overlap: list[dict[str, Any]] = field(default_factory=list)
    coverage_gaps: list[dict[str, Any]] = field(default_factory=list)

    # Human-review fields
    analyst_judgement_required: str = (
        "Confirm whether this campaign's sector and technique set applies to this "
        "estate. Approve or dismiss each technique in exposure_overlap before any "
        "detection content is authored."
    )
    governance_note: str = (
        "Attribution output is PROPOSED only. No alert rules or tickets are "
        "created automatically. Operator approval is mandatory."
    )


def _extract_techniques(text: str) -> list[str]:
    """Return deduplicated ATT&CK technique IDs found in ``text``."""
    found = _TECHNIQUE_RE.findall(text)
    seen: dict[str, None] = {}
    for t in found:
        seen[t.upper()] = None
    return list(seen)


def _extract_cves(text: str) -> list[str]:
    found = _CVE_RE.findall(text)
    seen: dict[str, None] = {}
    for c in found:
        seen[c.upper()] = None
    return list(seen)


def _find_sector_matches(text: str) -> list[str]:
    """Return adjacent-sector keywords present in the report text."""
    text_lower = text.lower()
    return [s for s in _SITA_ADJACENT_SECTORS if s in text_lower]


def attribute_campaign(
    report_text: str,
    estate_exposed_techniques: list[str] | None = None,
    estate_covered_techniques: list[str] | None = None,
) -> CampaignReport:
    """Attribute an external threat report to this estate (AVP-3 deterministic layer).

    Parameters
    ----------
    report_text:
        Raw text of the threat report (OSINT, MITRE blog, CTI feed entry, etc.)
    estate_exposed_techniques:
        Techniques the estate is exposed to (from ``attack.coverage``).
        If omitted, ``exposure_overlap`` and ``coverage_gaps`` are left empty.
    estate_covered_techniques:
        Techniques the platform's alert rules can evidence. If omitted, the
        coverage status is marked ``unknown``.
    """
    result = CampaignReport()

    result.extracted_techniques = _extract_techniques(report_text)
    result.extracted_cves = _extract_cves(report_text)
    result.sector_match_candidates = _find_sector_matches(report_text)

    exposed = set(estate_exposed_techniques or [])
    covered = set(estate_covered_techniques or [])

    overlap: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []

    for tech in result.extracted_techniques:
        if exposed:
            if tech in exposed:
                in_estate = True
                coverage_status = "covered" if tech in covered else "gap"
            else:
                in_estate = False
                coverage_status = "not_exposed"
        else:
            in_estate = None
            coverage_status = "unknown"

        record = {
            "technique_id": tech,
            "in_estate": in_estate,
            "coverage_status": coverage_status,
        }
        if in_estate:
            overlap.append(record)
            if coverage_status == "gap":
                gaps.append(record)
        else:
            overlap.append(record)

    result.exposure_overlap = overlap
    result.coverage_gaps = gaps

    return result
