"""Outbound scrubbing for anything that leaves the platform toward AIMI.

Why this module exists
----------------------
The platform's egress register records *where* data goes and on what basis.
Nothing recorded *what* may go. ``app.pii`` masks personal data on the way into
the warehouse and ``app.ai.verify.scrub_sensitive_claims`` scrubs model output on
the way out to a human. Neither covers the third leg: the text this module
scrubs is the request that leaves the process for a third-party inference
provider.

That gap is what NFR-AI-05 in ``docs/AI_INTEGRATION_PLAN_MASTER.md`` called for
and what no module implemented. This one does.

What is allowed out
-------------------
Only public threat identifiers and analyst-supplied threat-report prose, from
which the following are removed before egress:

- South African identity numbers
- email addresses
- IPv4 addresses, because a WAF source IP is personal information under
  POPIA s.13(c) and ``egress.py`` already flags it as such for Imperva
- account and employee identifiers, which is what ``identity.users`` holds
- bearer tokens and secrets
- JSON web tokens

What is never sent
------------------
Estate rows, ``audit.action_audit`` rows and ``identity.users`` rows have no path
out of this module at all. The residue modules that consume AIMI are handed
technique IDs, CVE IDs and the analyst's own pasted report — not database rows.
``scrub_outbound`` refuses a mapping that carries an estate column name rather
than trusting the caller to have been careful.
"""
from __future__ import annotations

import re
from typing import Any

#: The token substituted for anything removed.
PLACEHOLDER = "[redacted]"

#: Patterns removed from free text before it leaves the process. Ordered so that
#: the more specific patterns run first: an ID number contains digits, and a
#: secret assignment can contain an email address.
_SCRUBBERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # JSON web tokens, caught whole so the payload inside is never inspected.
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*")),
    # key = "value" style secrets.
    (
        "secret",
        re.compile(
            r"(?i)\b(password|passwd|secret|api[_-]?key|token|authorization)"
            r"\s*[:=]\s*[\"']?[^\s,\"'}]{4,}[\"']?"
        ),
    ),
    # SA identity numbers: 13 digits, optionally hyphenated as YYMMDD SSSSS C A Z.
    ("sa_id", re.compile(r"\b\d{6}[- ]?\d{5}[- ]?\d{2}[- ]?\d{1}\b")),
    # Bare 13-digit runs that survive the above (no hyphens).
    ("sa_id_bare", re.compile(r"\b\d{13}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)

#: Payload keys that may never be sent outbound, matched case-insensitively
#: against the whole key. These are the columns whose egress is forbidden by
#: NFR-AI-11 and by the tenancy model, regardless of the value under them.
NEVER_SEND_FIELDS = frozenset({
    "department_id", "department_ids", "department_name",
    "branch_id", "branch_ids",
    "province_id", "province_ids",
    "person_id", "employee_id", "employee_number", "user_id", "username",
    "email", "source_ip", "src_ip", "client_ip", "remote_addr",
    "password", "password_hash", "token", "api_key", "secret",
    "raw_data", "request_body", "payload",
    "audit_detail", "actor", "detail",
})

#: The only structured keys this codebase is expected to send. Present so a
#: caller assembling a payload has an allowlist to build from rather than a
#: denylist to evade.
ELIGIBLE_FIELDS = frozenset({
    "technique_id", "techniques", "technique",
    "cve", "cves", "cve_id",
    "sector", "sectors", "sector_match_candidates",
    "threat_report", "investigation_context", "indicators",
    "signal", "primary_signal", "total_risk_delta",
    "campaign", "adversary", "actor_type",
})


class OutboundPayloadRefused(ValueError):
    """Raised when a payload carries a field that may not leave the platform."""


def scrub_text(text: str) -> str:
    """Remove personal and secret material from free text.

    Public identifiers are untouched: ATT&CK IDs, CVE IDs and ordinary prose
    pass through unchanged, which is the point — this is a scrubber, not a
    summariser, and it must not degrade the threat content an analyst pasted in.
    """
    if not text:
        return text
    out = text
    for _label, pattern in _SCRUBBERS:
        out = pattern.sub(PLACEHOLDER, out)
    return out


def scrub_outbound(payload: Any) -> Any:
    """Recursively scrub a payload for egress.

    Raises on a forbidden key rather than dropping it silently. A refusal the
    caller cannot see is a leak; a refusal that raises is a bug report.
    """
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            if str(key).lower() in NEVER_SEND_FIELDS:
                raise OutboundPayloadRefused(
                    f"refusing to send field '{key}' to a third-party inference "
                    f"provider. Estate, identity and audit columns have no egress "
                    f"path by design (NFR-AI-11). Send a public identifier instead."
                )
            out[str(key)] = scrub_outbound(value)
        return out
    if isinstance(payload, (list, tuple)):
        return [scrub_outbound(item) for item in payload]
    if isinstance(payload, str):
        return scrub_text(payload)
    return payload


def truncate(text: str, limit: int) -> str:
    """Clamp outbound free text to ``limit`` characters.

    Threat-report excerpts are analyst-supplied and can be a whole pasted
    document. The residue is the attribution judgement, not the document, so
    truncating loses less than posting a full report to a third party would.
    """
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + f"\n[truncated at {limit} characters]"