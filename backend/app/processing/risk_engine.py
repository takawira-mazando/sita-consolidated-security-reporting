import math
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

#: Human-facing labels for the four fused signals, keyed by signal name.
SIGNAL_LABELS = {
    "appscan": "AppScan severity",
    "imperva": "Imperva violations",
    "exposure": "API exposure",
    "compliance": "Compliance gap",
}

# Canonical risk band edges. These are the only bucket thresholds in the
# platform; anything that needs to describe a band to a human must read them
# from here rather than restating a number.
SAFE_MAX = 30.0
MONITORED_MAX = 70.0

APPSCAN_CEILING_PERCENTILE = 99.0
APPSCAN_CEILING_FLOOR = 1.0
DEFAULT_APPSCAN_CEILING = 5.0

def weighted_severity_total(counts: dict[str, int]) -> float:
    return float(sum(SEVERITY_WEIGHTS.get(k, 0) * v for k, v in counts.items()))

def calibrate_appscan_ceiling(
    weighted_totals: list[float],
    percentile: float = APPSCAN_CEILING_PERCENTILE,
    floor: float = APPSCAN_CEILING_FLOOR,
) -> float:
    """Derive the AppScan signal ceiling from observed estate volume.

    The ceiling is the given percentile of per-application weighted severity
    totals, so the scale tracks the estate instead of a fixed constant. It is
    floored so a near-clean estate cannot collapse the scale to near-zero and
    inflate every score.
    """
    positive = sorted(float(t) for t in weighted_totals if t and t > 0)
    if not positive:
        return floor
    if len(positive) == 1:
        return max(positive[0], floor)
    rank = (percentile / 100.0) * (len(positive) - 1)
    lower, upper = math.floor(rank), math.ceil(rank)
    if lower == upper:
        return max(positive[lower], floor)
    ceiling = positive[lower] + (positive[upper] - positive[lower]) * (rank - lower)
    return max(ceiling, floor)

def compute_signal_appscan(counts: dict[str, int], max_score: float | None = None) -> float:
    ceiling = DEFAULT_APPSCAN_CEILING if max_score is None else float(max_score)
    weighted = weighted_severity_total(counts)
    return min((weighted / ceiling) * 100, 100) if ceiling > 0 else 0.0

def compute_signal_imperva(count: int) -> float:
    if count <= 0:
        return 0.0
    return min(np.log2(count + 1) * 10, 100)

def compute_signal_exposure(scores: list[float]) -> float:
    return float(np.mean(scores)) if scores else 0.0

def compute_signal_compliance(pct: float) -> float:
    return 100.0 - pct

def fused_risk(
    inputs: RiskInputs,
    weights: dict[str, float] | None = None,
    appscan_ceiling: float | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS
    sa = compute_signal_appscan(inputs.appscan_severity_counts, appscan_ceiling)
    si = compute_signal_imperva(inputs.imperva_violation_count)
    e = compute_signal_exposure(inputs.api_exposure_scores)
    c = compute_signal_compliance(inputs.compliance_pct)
    total_weight = sum(w.values())
    fused = (w["appscan"] * sa + w["imperva"] * si + w["exposure"] * e + w["compliance"] * c) / total_weight
    return round(float(np.clip(fused, 0, 100)), 1)

def risk_bucket(score: float) -> str:
    if score <= SAFE_MAX:
        return "safe"
    elif score <= MONITORED_MAX:
        return "monitored"
    return "critical"
