"""Tests for the AIMI gateway, its egress control, and the two wired residues.

Three things are being protected here, in order of importance.

1. **Nothing leaves that should not.** The redaction module is the only thing
   standing between a database column and a third-party inference provider, and
   its job is easier to break silently than to break loudly. These tests assert
   refusals, not just scrubbed output, because a refusal that does not raise is
   a leak.

2. **Nothing runs when it should not.** AIMI is off by default, and a deployment
   with no key must be byte-for-byte indistinguishable from one with no AIMI
   dependency. That is the property that lets the deterministic layer be signed.

3. **A provider failure is not a route failure.** Every transient path returns
   ``None`` and the deterministic answer survives. An analyst mid-incident
   should never see a 500 because a third party is slow.
"""
from __future__ import annotations

import json

import pytest
from app.ai.aimi import gateway
from app.ai.aimi.enrichment import (
    UNAVAILABLE_BREAKER,
    UNAVAILABLE_DISABLED,
    UNAVAILABLE_NO_RESULT,
    UNAVAILABLE_PROVIDER,
    UNAVAILABLE_UNSAFE_PAYLOAD,
    enrich_campaign_attribution,
    enrich_risk_delta_causal,
)
from app.ai.aimi.redaction import (
    ELIGIBLE_FIELDS,
    NEVER_SEND_FIELDS,
    OutboundPayloadRefused,
    scrub_outbound,
    scrub_text,
    truncate,
)
from app.monitoring.egress import EgressNotPermitted, get


@pytest.fixture(autouse=True)
def _closed_breaker():
    """No test should inherit another test's circuit state."""
    gateway.reset_circuit()
    yield
    gateway.reset_circuit()


@pytest.fixture
def enabled(monkeypatch):
    """A configured, enabled AIMI that never touches the network."""
    from app.config import settings

    monkeypatch.setattr(settings, "aimi_enabled", True)
    monkeypatch.setattr(
        settings, "aimi_api_key",
        type(settings).model_fields["aimi_api_key"].annotation(
            "aimi_test_key_not_a_real_credential"
        ),
    )
    return settings


# ---------------------------------------------------------------------------
# 1. Outbound redaction — the control that must not regress
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text, must_vanish", [
    ("Contact jane.doe@provincial.gov.za about T1190", "jane.doe@provincial.gov.za"),
    ("Source 41.203.71.144 triggered T1059", "41.203.71.144"),
    ("ID 8001015009087 in the breach", "8001015009087"),
    ("Authorization: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig", "eyJhbGciOiJIUzI1NiJ9"),
    ("password=hunter2xyz leaked", "hunter2xyz"),
])
def test_scrub_text_removes_personal_and_secret_material(text, must_vanish):
    assert must_vanish not in scrub_text(text)


def test_scrub_text_preserves_the_threat_content_the_analyst_pasted():
    """The residue is the attribution judgement, not the document.

    If scrubbing degraded ATT&CK and CVE identifiers, it would be destroying the
    very content AIMI was called to read.
    """
    text = "Campaign BADNOTE exploits T1190 and T1059.001, tracked as CVE-2024-21762."
    scrubbed = scrub_text(text)
    for token in ("T1190", "T1059.001", "CVE-2024-21762"):
        assert token in scrubbed


@pytest.mark.parametrize("field", sorted(NEVER_SEND_FIELDS))
def test_outbound_refuses_every_forbidden_field(field):
    with pytest.raises(OutboundPayloadRefused):
        scrub_outbound({field: "anything"})


def test_outbound_refusal_names_the_offending_field():
    with pytest.raises(OutboundPayloadRefused, match="department_id"):
        scrub_outbound({"department_id": "dept-001"})


def test_outbound_refusal_reaches_through_nesting():
    """Nesting is how a leak gets in. A top-level check alone is not a control."""
    with pytest.raises(OutboundPayloadRefused):
        scrub_outbound({"a": {"b": [{"source_ip": "10.0.0.1"}]}})


def test_outbound_scrubs_free_text_inside_an_allowed_payload():
    out = scrub_outbound({"technique_id": "T1190", "threat_report": "from 10.1.2.3"})
    assert out["technique_id"] == "T1190"
    assert "10.1.2.3" not in out["threat_report"]


def test_eligible_fields_are_a_subset_of_what_is_not_forbidden():
    """The allowlist a caller builds from must itself be sendable."""
    assert ELIGIBLE_FIELDS.isdisjoint(NEVER_SEND_FIELDS)


def test_truncate_bounds_an_oversized_report():
    long_text = "T1190 " * 5000
    bounded = truncate(long_text, 100)
    assert len(bounded) < 200
    assert "truncated" in bounded


# ---------------------------------------------------------------------------
# 2. The gateway must be inert unless enabled and allowlisted
# ---------------------------------------------------------------------------


def test_gateway_is_inert_by_default():
    """No environment sets AIMI_ENABLED, so the default is the shipped state."""
    from app.config import settings

    assert settings.aimi_enabled is False
    assert gateway.is_available() is False


def test_call_tool_refuses_when_disabled(enabled, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "aimi_enabled", False)
    with pytest.raises(gateway.AimiNotEnabled):
        gateway.call_tool("tool_aimi_ioc_correlate", {"iocs_json": "[]"})


@pytest.mark.parametrize("tool", sorted(gateway.REFUSED_TOOLS))
def test_dangerous_tools_are_refused_even_when_enabled(enabled, tool):
    """Server-side code execution and policy mutation are never reachable here.

    AIMI's catalogue is larger than this platform's needs and can grow upstream.
    An allowlist is the only safe default; a denylist would need to know about
    every tool the provider adds.
    """
    with pytest.raises(gateway.AimiToolNotAllowed):
        gateway.call_tool(tool, {})


def test_an_unlisted_tool_is_refused(enabled):
    with pytest.raises(gateway.AimiToolNotAllowed, match="allowlist"):
        gateway.call_tool("tool_aimi_web_search", {"query": "x"})


def test_allowed_tools_are_a_subset_of_nothing_forbidden(enabled):
    assert gateway.ALLOWED_TOOLS.isdisjoint(gateway.REFUSED_TOOLS)


def test_gateway_does_not_call_the_provider_when_the_breaker_is_open(enabled):
    """A provider that is already failing should not be called again."""
    for _ in range(gateway.circuit().threshold):
        gateway._state.record_failure()
    assert gateway.circuit().is_open is True
    assert gateway.is_available() is False
    assert gateway.call_tool("tool_aimi_ioc_correlate", {"iocs_json": "[]"}) is None


def test_breaker_closes_after_a_success(enabled):
    gateway._state.record_failure()
    gateway._state.record_failure()
    gateway._state.record_success()
    assert gateway.circuit().is_open is False


def test_breaker_reopens_once_the_cooldown_has_passed(enabled):
    for _ in range(gateway.circuit().threshold):
        gateway._state.record_failure()
    assert gateway.circuit().is_open is True
    # Rewind the opening past the cooldown rather than sleeping through it.
    gateway._state.opened_at -= gateway.circuit().cooldown_seconds + 1
    assert gateway.circuit().is_open is False


# ---------------------------------------------------------------------------
# 3. Egress registration
# ---------------------------------------------------------------------------


def test_aimi_is_in_the_transfer_register():
    dest = get("aimi")
    assert dest.host == "aimiafrica.cloud"
    assert dest.direction == "push"
    assert dest.module == "app.ai.aimi.gateway"
    assert dest.authorised is True


def test_aimi_register_entry_records_the_outbound_data_classes():
    """A transfer basis with no statement of what moves is not a transfer basis."""
    dest = get("aimi")
    assert dest.data_classes
    assert dest.transfer_mechanism
    assert "ATT&CK" in " ".join(dest.data_classes)


def test_the_gateway_targets_a_registered_destination():
    """The id the gateway checks must be the id the register defines.

    A typo here would make the egress check pass against nothing.
    """
    assert get(gateway.EGRESS_DESTINATION_ID).id == "aimi"


def test_unregistering_aimi_stops_the_gateway(enabled, monkeypatch):
    """Fail closed: an unregistered destination must not be reachable."""
    from app.monitoring.egress import TRANSFER_REGISTER

    monkeypatch.delitem(TRANSFER_REGISTER, "aimi")
    with pytest.raises(EgressNotPermitted):
        gateway.call_tool("tool_aimi_ioc_correlate", {"iocs_json": "[]"}, timeout=0.1)


# ---------------------------------------------------------------------------
# 4. Enrichment degrades, and never raises
# ---------------------------------------------------------------------------


def test_campaign_enrichment_is_absent_when_disabled():
    out = enrich_campaign_attribution("exploits T1190", ["T1190"], [], ["government"], [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_DISABLED


def test_campaign_enrichment_skips_correlation_with_nothing_to_correlate(enabled):
    """No identifiers means no IOCs; calling anyway would burn a request for nothing."""
    out = enrich_campaign_attribution("prose only", [], [], [], [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_NO_RESULT


def test_campaign_enrichment_reports_a_provider_failure_rather_than_raising(enabled):
    """A provider outage must not become a 500 to an analyst."""
    out = enrich_campaign_attribution(
        "exploits T1190", ["T1190"], [], ["government"],
        [{"technique_id": "T1190", "in_estate": True}],
    )
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_PROVIDER


def test_a_transport_failure_is_not_reported_as_an_empty_answer(enabled):
    """'unreachable' and 'returned nothing' are different faults.

    An operator triaging a provider incident needs to know which one happened;
    collapsing both into one string loses that.
    """
    assert UNAVAILABLE_PROVIDER != UNAVAILABLE_NO_RESULT


def test_an_answered_but_blank_result_is_reported_as_no_result(enabled, monkeypatch):
    monkeypatch.setattr(
        gateway, "call_tool",
        lambda *a, **k: {"content": [{"type": "text", "text": "   "}]},
    )
    out = enrich_campaign_attribution("exploits T1190", ["T1190"], [], [], [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_NO_RESULT


def test_campaign_enrichment_is_blocked_by_an_unsafe_payload(enabled, monkeypatch):
    """If redaction refuses, the answer is 'not enriched', never 'sent anyway'."""

    def _refuse(*_args, **_kwargs):
        raise OutboundPayloadRefused("refusing to send field 'department_id'")

    monkeypatch.setattr(gateway, "call_tool", _refuse)
    out = enrich_campaign_attribution("exploits T1190", ["T1190"], [], [], [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_UNSAFE_PAYLOAD


def test_risk_delta_enrichment_needs_a_mapped_technique(enabled):
    """Without a technique there is nothing to ask about."""
    out = enrich_risk_delta_causal("app", 12.5, "unmapped_signal", None, [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_NO_RESULT


def test_risk_delta_enrichment_is_absent_when_disabled():
    out = enrich_risk_delta_causal("app", 12.5, "appscan", "T1190", [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_DISABLED


def test_enrichment_short_circuits_while_the_breaker_is_open(enabled, monkeypatch):
    """A provider that is already failing must not be called again."""
    for _ in range(gateway.circuit().threshold):
        gateway._state.record_failure()

    def _must_not_be_called(*_args, **_kwargs):
        raise AssertionError("the provider was called while the breaker was open")

    monkeypatch.setattr(gateway, "call_tool", _must_not_be_called)
    out = enrich_campaign_attribution("exploits T1190", ["T1190"], [], [], [])
    assert out["enriched_by_model"] is False
    assert out["reason"] == UNAVAILABLE_BREAKER


def test_enrichment_never_sends_the_local_measurement(enabled, monkeypatch):
    """The delta is this estate's number. It is computed here and stays here.

    AIMI is asked what the technique means, not what this application scored —
    which keeps the outbound set to public constants plus the analyst's paste.
    """
    captured: dict = {}

    def _capture(tool, arguments, **_kwargs):
        captured["tool"] = tool
        captured["arguments"] = arguments
        return {"content": [{"type": "text", "text": "Exploitation of a public app."}]}

    monkeypatch.setattr(gateway, "call_tool", _capture)
    out = enrich_risk_delta_causal("Home Affairs Portal", 41.2, "appscan", "T1190", [])

    assert out["enriched_by_model"] is True
    assert out["tool"] == "tool_aimi_playbook_attack"
    payload = json.dumps(captured["arguments"])
    assert "Home Affairs Portal" not in payload
    assert "41.2" not in payload
    assert "T1190" in payload


def test_campaign_enrichment_sends_identifiers_but_not_the_estate_name(enabled, monkeypatch):
    captured: dict = {}

    def _capture(tool, arguments, **_kwargs):
        captured["tool"] = tool
        captured["arguments"] = arguments
        return {"content": [{"type": "text", "text": "Targets government services."}]}

    monkeypatch.setattr(gateway, "call_tool", _capture)
    out = enrich_campaign_attribution(
        "exploits T1190 and CVE-2024-21762 against government",
        ["T1190"], ["CVE-2024-21762"], ["government"],
        [{"technique_id": "T1190", "in_estate": True}],
    )

    assert out["enriched_by_model"] is True
    assert out["tool"] == "tool_aimi_ioc_correlate"
    assert out["analyst_review_required"] is True
    payload = json.dumps(captured["arguments"])
    assert "T1190" in payload
    assert "CVE-2024-21762" in payload


# ---------------------------------------------------------------------------
# 5. The deterministic modules stay free of a provider
# ---------------------------------------------------------------------------


def test_residue_modules_do_not_import_the_gateway():
    """The guard TestNoModelImports provides, applied to the residue modules.

    campaign.py and causal.py accept an already-enriched payload. If either ever
    imports app.ai.aimi, the deterministic layer becomes unrunnable without the
    provider and the property the whole architecture rests on is gone.
    """
    import ast
    import importlib
    import inspect

    for module_name in ("app.processing.intel.campaign", "app.processing.intel.causal"):
        tree = ast.parse(inspect.getsource(importlib.import_module(module_name)))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        offenders = {n for n in imported if n.startswith(("app.ai.aimi", "httpx", "requests", "aiohttp"))}
        assert not offenders, f"{module_name} reaches the provider via {sorted(offenders)}"


def test_capability_manifest_separates_wired_from_unwired_residue():
    """A declared residue and a served residue are different states.

    Reporting them as one number would overstate what the platform does, which is
    the specific failure this registry exists to prevent.
    """
    from app.processing.intel import capability

    manifest = capability.manifest()
    assert manifest["residue_backed_by_provider"] == ["AVP-3", "AVP-8"]
    assert manifest["residue_declared_but_unwired"] == ["AVP-2", "AVP-5", "AVP-11"]
    for avp in manifest["residue_declared_but_unwired"]:
        prop = next(p for p in manifest["propositions"] if p["avp"] == avp)
        assert prop["residue_not_wired_because"], f"{avp} needs a recorded reason"
        assert not prop["residue_backed_by"]


def test_avp11_remains_unaided_because_the_payload_is_forbidden():
    """NFR-AI-11 is why AVP-11 is not wired, and that must stay explicit.

    If someone later relaxes it, the reason needs to be lifted deliberately
    rather than drifted past.
    """
    from app.processing.intel import capability

    prop = capability.get("AVP-11")
    assert not prop.residue_backed_by
    assert "NEVER_READ" in prop.residue_not_wired_because
    assert "action_audit" in prop.residue_not_wired_because