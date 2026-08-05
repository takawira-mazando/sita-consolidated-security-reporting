"""Tests for the fused risk engine (weighted signal computation + bucketing)."""
from __future__ import annotations

from app.processing.risk_engine import (
    RiskInputs,
    compute_signal_appscan,
    compute_signal_compliance,
    compute_signal_exposure,
    compute_signal_imperva,
    fused_risk,
    risk_bucket,
)


def test_risk_bucket_thresholds():
    assert risk_bucket(30) == "safe"
    assert risk_bucket(31) == "monitored"
    assert risk_bucket(70) == "monitored"
    assert risk_bucket(71) == "critical"


def test_appscan_signal_scales_with_severity():
    low = compute_signal_appscan({"low": 10})
    high = compute_signal_appscan({"critical": 10})
    assert high > low


def test_imperva_signal_log_scale():
    assert compute_signal_imperva(0) == 0
    assert compute_signal_imperva(100) > compute_signal_imperva(10)
    assert compute_signal_imperva(1_000_000) <= 100


def test_exposure_and_compliance_signals():
    assert compute_signal_exposure([]) == 0.0
    assert compute_signal_exposure([50.0]) == 50.0
    assert compute_signal_compliance(100.0) == 0.0
    assert compute_signal_compliance(80.0) == 20.0


def test_fused_risk_bounds():
    low = RiskInputs(
        appscan_severity_counts={"low": 1},
        imperva_violation_count=0,
        api_exposure_scores=[0.0],
        compliance_pct=100.0,
    )
    high = RiskInputs(
        appscan_severity_counts={"critical": 100},
        imperva_violation_count=1_000_000,
        api_exposure_scores=[100.0],
        compliance_pct=0.0,
    )
    assert fused_risk(low) < fused_risk(high)
    assert 0 <= fused_risk(low) <= 100
    assert 0 <= fused_risk(high) <= 100


def test_fused_risk_is_deterministic():
    inputs = RiskInputs(
        appscan_severity_counts={"high": 4, "medium": 3},
        imperva_violation_count=50,
        api_exposure_scores=[60.0, 80.0],
        compliance_pct=85.0,
    )
    assert fused_risk(inputs) == fused_risk(inputs)


def test_custom_weights():
    inputs = RiskInputs(
        appscan_severity_counts={"critical": 10},
        imperva_violation_count=0,
        api_exposure_scores=[],
        compliance_pct=100.0,
    )
    default = fused_risk(inputs)
    appscan_only = fused_risk(inputs, {"appscan": 1.0, "imperva": 0.0, "exposure": 0.0, "compliance": 0.0})
    assert appscan_only >= default
