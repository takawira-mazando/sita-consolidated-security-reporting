"""Tests for the anonymised provincial peer-benchmark builder."""
from __future__ import annotations

from app.api.routers.benchmark import _bucket, _build_benchmark


def _records(n=1, dept="gp-health", app="gp-health-core", score=80.0):
    rows = []
    for i in range(n):
        rows.append({
            "department_id": dept,
            "app_name": f"{app}-{i}" if i else app,
            "fused_score": score,
            "signal_appscan": 90.0,
            "signal_imperva": 85.0,
            "signal_api_exposure": 70.0,
            "signal_compliance_penalty": 60.0,
        })
    return rows


class TestBucket:
    def test_critical(self):
        assert _bucket(70) == "critical"
        assert _bucket(99.9) == "critical"

    def test_monitored(self):
        assert _bucket(45) == "monitored"
        assert _bucket(69.9) == "monitored"

    def test_safe(self):
        assert _bucket(0) == "safe"
        assert _bucket(44.9) == "safe"


class TestBuildBenchmark:
    def test_national_view_sees_every_province_unblinded(self):
        rows = _records(1, "gp-health") + _records(1, "wc-health", score=60.0)
        out = _build_benchmark(rows, caller_provinces=set(), nationwide=True)
        assert out["viewer"] == "national"
        assert len(out["leaderboard"]) == 2
        labels = [e["label"] for e in out["leaderboard"]]
        assert "Gauteng" in labels and "Western Cape" in labels
        assert all(e["province_id"] for e in out["leaderboard"])
        assert out["own"] is None

    def test_province_view_anonymises_peers(self):
        rows = (
            _records(1, "gp-health", score=90.0)
            + _records(1, "wc-health", score=80.0)
            + _records(1, "wc-education", score=70.0)
            + _records(1, "ec-health", score=50.0)
        )
        out = _build_benchmark(rows, caller_provinces={"gp"}, nationwide=False)
        assert out["viewer"] == "province"
        # gp leader (90) is "you"; wc is mean(80,70)=75 -> Peer A; ec -> Peer B
        you = [e for e in out["leaderboard"] if e["is_you"]]
        assert len(you) == 1 and you[0]["province_id"] == "gp"
        assert you[0]["label"] == "Gauteng"
        peers = [e for e in out["leaderboard"] if not e["is_you"]]
        assert [e["label"] for e in peers] == ["Peer Province A", "Peer Province B"]
        assert all(e["province_id"] is None for e in peers)

    def test_own_has_department_drilldown(self):
        rows = _records(1, "gp-health", score=90.0) + _records(1, "wc-health", score=80.0)
        out = _build_benchmark(rows, caller_provinces={"gp"}, nationwide=False)
        assert out["own"]["province_id"] == "gp"
        assert out["own"]["departments"][0]["department_id"] == "gp-health"
        assert out["own"]["departments"][0]["app_count"] == 1
        assert "AppScan" in out["own"]["departments"][0]["primary_driver"]

    def test_peer_rows_contain_no_raw_components(self):
        rows = _records(1, "gp-health") + _records(1, "wc-health", score=60.0)
        out = _build_benchmark(rows, caller_provinces={"gp"}, nationwide=False)
        for peer in [e for e in out["leaderboard"] if not e["is_you"]]:
            assert set(peer) == {"rank", "label", "province_id", "fused_score", "bucket", "is_you"}
            assert "signal" not in peer
        assert "aggregated fused risk score" in out["note"]

    def test_national_average(self):
        rows = _records(1, "gp-health", score=90.0) + _records(1, "wc-health", score=70.0)
        out = _build_benchmark(rows, caller_provinces={"gp"}, nationwide=True)
        assert out["national_average"] == 80.0

    def test_national_departments_are_excluded(self):
        rows = _records(1, "gp-health", score=90.0) + _records(1, "treasury", score=10.0)
        out = _build_benchmark(rows, caller_provinces=set(), nationwide=True)
        assert len(out["leaderboard"]) == 1
        assert out["leaderboard"][0]["province_id"] == "gp"

    def test_empty_input(self):
        out = _build_benchmark([], caller_provinces={"gp"}, nationwide=False)
        assert out["leaderboard"] == []
        assert out["national_average"] is None
        assert out["own"] is None
