"""Tests for the Auditor-General aggregation-only compliance export engine."""
from __future__ import annotations

from datetime import date

from app.api.routers.exports_ag import build_attestation, canonical_json, sha256_hex


class _Row:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def _snapshot():
    return _Row(
        framework="popia",
        snapshot_date=date(2026, 7, 31),
        overall_score="84.0",
        passed_controls=18,
        total_controls=20,
        details={"data_inventory": 88, "consent": 76, "retention": 81},
    )


def _gaps():
    return [
        _Row(framework="popia", status="open", severity="high", domain="consent"),
        _Row(framework="popia", status="open", severity="high", domain="consent"),
        _Row(framework="popia", status="in_progress", severity="medium", domain="retention"),
    ]


def _risk_rows(n=2):
    rows = []
    for i in range(n):
        rows.append({
            "department_id": "gp-health",
            "app_name": f"app-{i}",
            "fused_score": 85.0,
            "signal_appscan": 80.0,
            "signal_imperva": 90.0,
            "signal_api_exposure": 70.0,
            "signal_compliance_penalty": 60.0,
        })
    return rows


class TestCanonicalHash:
    def test_sha256_hex_is_64_chars(self):
        h = sha256_hex({"a": 1, "b": [1, 2]})
        assert len(h) == 64
        import re
        assert re.fullmatch(r"[0-9a-f]{64}", h)

    def test_hash_is_key_order_independent(self):
        assert sha256_hex({"a": 1, "b": 2}) == sha256_hex({"b": 2, "a": 1})

    def test_hash_changes_when_payload_changes(self):
        assert sha256_hex({"a": 1}) != sha256_hex({"a": 2})

    def test_canonical_json_stable(self):
        assert canonical_json({"x": 1, "y": [1, 2]}) == '{"x":1,"y":[1,2]}'


class TestBuildAttestation:
    def test_aggregates_controls(self):
        out = build_attestation(
            "popia", _snapshot(), _gaps(), _risk_rows(),
            {"type": "estate", "provinces": ["all"], "note": ""},
        )
        assert out["artifact"] == "AG compliance attestation (aggregate only)"
        assert out["framework"] == "popia"
        assert out["controls"]["gap_total"] == 3
        assert out["controls"]["status_counts"] == {"in_progress": 1, "open": 2}
        assert out["controls"]["severity_counts"] == {"high": 2, "medium": 1}
        assert out["controls"]["domain_counts"] == {"consent": 2, "retention": 1}

    def test_snapshot_scores(self):
        out = build_attestation("popia", _snapshot(), [], [], {"type": "estate", "provinces": ["all"], "note": ""})
        assert out["snapshot"]["overall_score"] == 84.0
        assert out["snapshot"]["passed_controls"] == 18
        assert out["snapshot"]["domain_scores"] == {"data_inventory": 88, "consent": 76, "retention": 81}

    def test_risk_profile_aggregates_only(self):
        out = build_attestation("popia", _snapshot(), [], _risk_rows(), {"type": "estate", "provinces": ["all"], "note": ""})
        profile = out["risk_profile"]
        assert profile["scoped_apps"] == 2
        assert profile["scoped_departments"] == 1
        assert profile["bucket_counts"] == {"critical": 2, "monitored": 0, "safe": 0}
        assert profile["signal_averages"]["appscan"] == 80.0
        # no per-row data leaks
        assert "app-0" not in canonical_json(out)

    def test_no_snapshot(self):
        out = build_attestation("popia", None, [], [], {"type": "estate", "provinces": ["all"], "note": ""})
        assert out["snapshot"] is None

    def test_provenance_strips_raw(self):
        out = build_attestation("popia", _snapshot(), _gaps(), _risk_rows(), {"type": "estate", "provinces": ["all"], "note": ""})
        assert "Aggregation-only" in out["provenance"]
        payload = canonical_json(out)
        for leak in ("sql_injection", "SQLi", "192.168", "id_number", "password"):
            assert leak.lower() not in payload.lower()
