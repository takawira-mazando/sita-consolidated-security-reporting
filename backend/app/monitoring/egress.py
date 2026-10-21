"""Cross-border data transfer register and egress enforcement.

Closes the code half of gap G-07 in ``docs/B5_ICASA_ECT_Gap_Analysis.md``.

The platform talks to eight external systems. Several of them move South African
government security data outside the Republic, and before this module nothing
recorded that fact: the PagerDuty endpoint was a hardcoded string literal with
no register, no jurisdiction and no lawful-basis record. ``cross_border`` was a
0.05 weight in a scoring function with no callers.

POPIA s.44 permits a transfer to a third party in a foreign country only on
conditions, and POPIA s.57(1)(e) makes prior authorisation from the Information
Regulator mandatory when transferring to a country without an adequate level of
protection. Jurisdiction and transfer-mechanism status are therefore recorded
per destination so the question can be answered without reading the code.

Design
------

- **Fail closed.** An unregistered destination raises rather than proceeding.
  An unregistered egress is exactly the failure this control exists to catch.
- **Non-blocking for notification channels.** A dispatch adapter that is blocked
  returns ``False`` and records the refusal, so an unregistered PagerDuty
  workspace degrades an alerting path rather than raising through a background
  worker. Ingest connectors, which have no user waiting on them, raise.
- **The register is code, not configuration.** It is reviewed, diffable and
  testable. Adding a destination is a code review event, which is the control
  point: you cannot add an overseas destination without a reviewer noticing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EgressDestination:
    """One external system the platform exchanges data with."""

    id: str
    host: str
    direction: str  # "pull" (we fetch) or "push" (we send)
    jurisdiction: str
    data_classes: tuple[str, ...]
    purpose: str
    transfer_mechanism: str
    #: False where a transfer agreement or prior authorisation is not yet on
    #: file. A False here does not block the connection — it makes the gap
    #: visible in the register and in the audit trail.
    authorised: bool
    module: str = ""
    notes: str = ""

    @property
    def cross_border(self) -> bool:
        return self.jurisdiction.lower() != "south africa"


#: The register. Every destination in the codebase must appear here.
#:
#: Reviewed as code so that adding an overseas destination is a pull request a
#: reviewer sees, rather than an environment variable.
TRANSFER_REGISTER: dict[str, EgressDestination] = {
    "appscan": EgressDestination(
        id="appscan",
        host="cloud.appscan.com",
        direction="pull",
        jurisdiction="United States",
        data_classes=("vulnerability findings", "application metadata", "raw OEM payload"),
        purpose="Retrieve SA government application security findings from HCL AppScan Cloud",
        transfer_mechanism="pending — no DPA or SCC on file",
        authorised=False,
        module="app.connectors.appscan",
        notes="Full OEM payload including identifiers is pulled into "
              "staging.raw_records and warehouse.findings.raw_data.",
    ),
    "imperva": EgressDestination(
        id="imperva",
        host="config-supplied",
        direction="pull",
        jurisdiction="configurable",
        data_classes=("WAF events", "source IP addresses", "request URIs"),
        purpose="Retrieve WAF block events and digital asset data",
        transfer_mechanism="pending — jurisdiction set by deployment config",
        authorised=False,
        module="app.connectors.imperva",
        notes="Source IPs and request URIs are personal information under "
              "POPIA s.13(c) and are retained with no TTL.",
    ),
    "apisec": EgressDestination(
        id="apisec",
        host="config-supplied",
        direction="pull",
        jurisdiction="configurable",
        data_classes=("API endpoint inventory"),
        purpose="Retrieve API exposure inventory",
        transfer_mechanism="pending — jurisdiction set by deployment config",
        authorised=False,
        module="app.connectors.apisec",
    ),
    "pagerduty": EgressDestination(
        id="pagerduty",
        host="events.pagerduty.com",
        direction="push",
        jurisdiction="United States",
        data_classes=("alert title", "alert description", "severity", "target identifier"),
        purpose="Escalate critical security incidents to the on-call responder",
        transfer_mechanism="pending — no DPA or SCC on file",
        authorised=False,
        module="app.dispatch.pagerduty_adapter",
        notes="Endpoint was a hardcoded string literal with no register entry. "
              "Critical-severity alerts only.",
    ),
    "teams": EgressDestination(
        id="teams",
        host="webhook-url-supplied",
        direction="push",
        jurisdiction="Microsoft-hosted",
        data_classes=("alert title", "alert description", "severity", "target identifier"),
        purpose="Notify the SOC team channel of security alerts",
        transfer_mechanism="pending — jurisdiction set by webhook destination",
        authorised=False,
        module="app.dispatch.teams_adapter",
        notes="Self-hosted Teams would move this in-border.",
    ),
    "ipapi": EgressDestination(
        id="ipapi",
        host="ipapi.co",
        direction="pull",
        jurisdiction="configurable",
        data_classes=("IP address being looked up"),
        purpose="Enrich a WAF source IP with geolocation for triage",
        transfer_mechanism="pending — jurisdiction set by deployment config",
        authorised=False,
        module="app.api.routers.admin",
        notes="Unaudited third-party lookup of a SA source IP address.",
    ),
    "smtp": EgressDestination(
        id="smtp",
        host="config-supplied",
        direction="push",
        jurisdiction="deployment-dependent",
        data_classes=("alert title", "alert description", "severity"),
        purpose="Email critical alerts to the SOC mailbox",
        transfer_mechanism="deployment-dependent",
        authorised=True,
        module="app.dispatch.email_adapter",
        notes="Onshore relay keeps this in-border. Recipient is a fixed "
              "internal address, not an end user, so ECT Act direct-marketing "
              "provisions are not engaged.",
    ),
    "aimi": EgressDestination(
        id="aimi",
        host="aimiafrica.cloud",
        direction="push",
        jurisdiction="South Africa",
        data_classes=(
            "ATT&CK technique identifiers",
            "CVE identifiers",
            "curated threat-report excerpts supplied by an analyst",
        ),
        purpose=(
            "Supply the AI residue for the gated value propositions: campaign "
            "attribution (AVP-3) and risk-delta causal attribution (AVP-8). "
            "The deterministic layer is computed locally and is never outsourced."
        ),
        transfer_mechanism=(
            "signed-off outbound data register entry and transfer basis "
            "(docs/AI_INTEGRATION_REQUIREMENTS.md D6, C7)"
        ),
        authorised=True,
        module="app.ai.aimi.gateway",
        notes="Outbound payloads are restricted to public threat identifiers "
              "and are scrubbed by app.ai.aimi.redaction before egress. Estate "
              "rows, audit rows and identity tables are not eligible: see "
              "app.ai.aimi.redaction.ELIGIBLE_FIELDS. Disabled unless "
              "AIMI_ENABLED is set, so a deployment with no key makes no call. "
              "AIMI's own sub-processor hosting jurisdiction is a separate "
              "question from this register entry and is not asserted here.",
    ),
}

#: Destinations holding a transfer agreement or authorisation on file. Two have
#: cleared: ``smtp`` (onshore relay) and ``aimi`` (signed-off outbound data
#: register entry under AI_INTEGRATION_REQUIREMENTS D6/C7). It exists so the
#: empty state was visible before anything cleared it, and so a regression that
#: empties it again is obvious.
AUTHORISED_DESTINATIONS = frozenset(
    dest.id for dest in TRANSFER_REGISTER.values() if dest.authorised
)


class EgressNotPermitted(RuntimeError):
    """Raised when code attempts an unregistered external destination."""


def get(destination_id: str) -> EgressDestination:
    """Look up a destination. Raises if it is not in the register."""
    try:
        return TRANSFER_REGISTER[destination_id]
    except KeyError:
        raise EgressNotPermitted(
            f"External destination '{destination_id}' is not in the cross-border "
            f"transfer register (app.monitoring.egress). Register it, or remove "
            f"the integration. Known destinations: {sorted(TRANSFER_REGISTER)}"
        ) from None


def check(destination_id: str) -> EgressDestination:
    """Return the destination, and warn when its transfer is not yet authorised.

    Unauthorised is a compliance gap to close, not a reason to break the
    integration — the platform still needs to reach AppScan and PagerDuty while
    the agreements are being papered. The warning is what makes it visible.
    """
    dest = get(destination_id)
    if not dest.authorised:
        logger.warning(
            "Egress to %s (%s, %s) has no transfer mechanism on file: %s",
            dest.id,
            dest.host,
            dest.jurisdiction,
            dest.transfer_mechanism,
        )
    return dest


def open_findings() -> list[dict]:
    """Every destination lacking a transfer mechanism — the working list."""
    return [
        {
            "id": d.id,
            "host": d.host,
            "direction": d.direction,
            "jurisdiction": d.jurisdiction,
            "cross_border": d.cross_border,
            "data_classes": list(d.data_classes),
            "transfer_mechanism": d.transfer_mechanism,
            "authorised": d.authorised,
            "notes": d.notes,
        }
        for d in TRANSFER_REGISTER.values()
        if not d.authorised
    ]