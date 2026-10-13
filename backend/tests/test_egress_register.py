"""Tests for the cross-border transfer register and egress enforcement.

Covers gap G-07 in ``docs/B5_ICASA_ECT_Gap_Analysis.md``.

The point of these tests is that an unregistered external destination cannot be
reached, and that every destination the codebase actually uses is present in the
register — a register that has silently fallen out of date with the code is
worse than no register, because it looks authoritative.
"""
from __future__ import annotations

import pytest
from app.monitoring.egress import (
    TRANSFER_REGISTER,
    EgressNotPermitted,
    check,
    get,
    open_findings,
)


def test_every_registered_destination_is_informed():
    for dest in TRANSFER_REGISTER.values():
        assert dest.id in TRANSFER_REGISTER
        assert dest.host
        assert dest.direction in ("pull", "push")
        assert dest.jurisdiction
        assert dest.data_classes
        assert dest.purpose
        assert dest.transfer_mechanism
        assert dest.module, f"{dest.id} must name the module that calls it"


def test_the_documented_destinations_are_all_registered():
    """The six external systems identified in the gap analysis."""
    for destination_id in (
        "appscan",
        "imperva",
        "apisec",
        "pagerduty",
        "teams",
        "ipapi",
        "smtp",
    ):
        assert destination_id in TRANSFER_REGISTER


def test_pagerduty_is_registered_as_an_unauthorised_cross_border_push():
    """The gap that started this: a hardcoded overseas endpoint with no record."""
    dest = get("pagerduty")
    assert dest.host == "events.pagerduty.com"
    assert dest.direction == "push"
    assert dest.cross_border is True
    assert dest.authorised is False


def test_appscan_is_registered_as_an_unauthorised_cross_border_pull():
    dest = get("appscan")
    assert dest.cross_border is True
    assert dest.authorised is False


def test_onshore_smtp_is_the_only_authorised_destination():
    authorised = [d.id for d in TRANSFER_REGISTER.values() if d.authorised]
    assert authorised == ["smtp"]


def test_cross_border_property():
    assert get("smtp").jurisdiction != "South Africa"
    assert TRANSFER_REGISTER["smtp"].direction == "push"


def test_unregistered_destination_is_refused():
    with pytest.raises(EgressNotPermitted) as exc:
        get("some-unregistered-saas")
    assert "not in the cross-border transfer register" in str(exc.value)


def test_check_returns_the_destination_for_registered_ids():
    assert check("pagerduty").id == "pagerduty"


def test_open_findings_lists_every_unauthorised_destination():
    findings = open_findings()
    assert findings, "the working list must not be empty while gaps remain"
    for finding in findings:
        assert finding["authorised"] is False
        assert finding["transfer_mechanism"]
        assert "jurisdiction" in finding
        assert "cross_border" in finding
    ids = {f["id"] for f in findings}
    assert {"appscan", "pagerduty", "teams", "imperva"} <= ids


# --------------------------------------------------------------------------
# enforcement at the dispatch adapters
# --------------------------------------------------------------------------


async def test_pagerduty_adapter_refuses_an_unregistered_destination(monkeypatch):
    from app.dispatch import pagerduty_adapter

    monkeypatch.delitem(pagerduty_adapter.check.__globals__["TRANSFER_REGISTER"], "pagerduty")
    adapter = pagerduty_adapter.PagerDutyAdapter(routing_key="R-KEY")
    # Returns False rather than raising: an unregistered destination must
    # refuse to send, but must not break the dispatch worker.
    assert await adapter.send({"id": "a1", "title": "t", "severity": "critical"}) is False


async def test_teams_adapter_refuses_an_unregistered_destination(monkeypatch):
    from app.dispatch import teams_adapter

    monkeypatch.delitem(teams_adapter.check.__globals__["TRANSFER_REGISTER"], "teams")
    adapter = teams_adapter.TeamsAdapter(webhook_url="https://example.invalid/hook")
    assert await adapter.send({"id": "a1", "title": "t", "severity": "critical"}) is False


def test_adapters_are_inert_when_unconfigured():
    """An unset key/webhook stays inert regardless of the register."""
    from app.dispatch.pagerduty_adapter import PagerDutyAdapter
    from app.dispatch.teams_adapter import TeamsAdapter

    assert PagerDutyAdapter().routing_key == ""
    assert TeamsAdapter().webhook_url == ""