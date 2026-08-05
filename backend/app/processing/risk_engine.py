from dataclasses import dataclass

import numpy as np


@dataclass
class RiskInputs:
    appscan_severity_counts: dict[str, int]
    imperva_violation_count: int
    api_exposure_scores: list[float]
    compliance_pct: float

DEFAULT_WEIGHTS = {"appscan": 0.35, "imperva": 0.25, "exposure": 0.20, "compliance": 0.20}
SEVERITY_WEIGHTS = {"critical": 1.0, "high": 0.6, "medium": 0.3, "low": 0.1}

def compute_signal_appscan(counts: dict[str, int], max_score: float = 100.0) -> float:
    weighted = sum(SEVERITY_WEIGHTS.get(k, 0) * v for k, v in counts.items())
    return min((weighted / max_score) * 100, 100) if max_score > 0 else 0.0

def compute_signal_imperva(count: int) -> float:
    if count <= 0:
        return 0.0
    return min(np.log2(count + 1) * 10, 100)

def compute_signal_exposure(scores: list[float]) -> float:
    return float(np.mean(scores)) if scores else 0.0

def compute_signal_compliance(pct: float) -> float:
    return 100.0 - pct

def fused_risk(inputs: RiskInputs, weights: dict[str, float] | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    sa = compute_signal_appscan(inputs.appscan_severity_counts)
    si = compute_signal_imperva(inputs.imperva_violation_count)
    e = compute_signal_exposure(inputs.api_exposure_scores)
    c = compute_signal_compliance(inputs.compliance_pct)
    total_weight = sum(w.values())
    fused = (w["appscan"] * sa + w["imperva"] * si + w["exposure"] * e + w["compliance"] * c) / total_weight
    return round(float(np.clip(fused, 0, 100)), 1)

def risk_bucket(score: float) -> str:
    if score <= 30:
        return "safe"
    elif score <= 70:
        return "monitored"
    return "critical"
