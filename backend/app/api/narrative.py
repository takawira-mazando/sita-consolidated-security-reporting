"""Canonical, self-describing platform model.

The dashboard narrative used to be hand-authored HTML in the frontend. That
narrative asserted facts about the platform -- signal weights, band thresholds,
department counts, framework domains -- as string literals. Nothing tested
them, so they rotted silently: the overlay claimed weights of 40/30/20/10 while
``risk_engine.DEFAULT_WEIGHTS`` was 35/25/20/20, claimed "60 departments"
against a 173-department catalogue, and claimed seven metrics were
"not tracked by the backend yet" when each had a live endpoint that the same
screen already rendered.

The fix is structural rather than editorial. Every number a human is shown about
*how the platform computes* now has exactly one home: the module that performs
the computation. This module assembles those constants into a descriptor the
frontend renders, so a weight change in ``risk_engine`` cannot desynchronise the
prose that describes it.

Scope note: this describes the *model*, not the *data*. It holds no tenant rows,
needs no database session, and every accessor is a plain import of an existing
constant. Tenant scoping (``tenant_filter``) is deliberately not involved --
there is nothing here to scope.
"""
from __future__ import annotations

import os
from functools import lru_cache

import yaml

from app.api.routers.compliance import EVIDENCE_EXPIRY_DAYS
from app.processing import compliance as compliance_engine
from app.processing import frameworks as framework_registry
from app.processing import owasp as owasp_taxonomy
from app.processing import risk_engine
from app.tenant import BRANCHES, CLUSTERS, DEPARTMENTS, MINISTRIES, PROVINCES

ALERT_RULES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "processing", "alert_rules.yaml"
)


@lru_cache(maxsize=1)
def _alert_rules() -> tuple[dict, ...]:
    try:
        with open(os.path.join(ALERT_RULES_PATH)) as fh:
            return tuple(yaml.safe_load(fh).get("rules", []))
    except (FileNotFoundError, yaml.YAMLError):
        return ()


def _risk_model() -> dict:
    return {
        "weights": dict(risk_engine.DEFAULT_WEIGHTS),
        "signal_labels": dict(risk_engine.SIGNAL_LABELS),
        "severity_weights": dict(risk_engine.SEVERITY_WEIGHTS),
        "bands": [
            {"bucket": "safe", "max": risk_engine.SAFE_MAX},
            {"bucket": "monitored", "max": risk_engine.MONITORED_MAX},
            {"bucket": "critical", "max": 100.0},
        ],
        "appscan_ceiling_percentile": risk_engine.APPSCAN_CEILING_PERCENTILE,
    }


def _compliance_model() -> dict:
    """Framework scoring weights plus the applicability determination.

    ``compliance_snapshots.overall_score`` is *seeded*, not computed --
    ``compute_framework_score`` has no callers. The weights below therefore
    describe the intended model, and the narrative says so rather than implying
    the displayed score is derived.
    """
    return {
        "weights": {
            "popia": dict(compliance_engine.POPIA_WEIGHTS),
            "iso_27001": dict(compliance_engine.ISO_WEIGHTS),
        },
        "frameworks": framework_registry.as_dicts(),
        "scores_are_seeded": True,
        "scored_by": None,
    }


def _alert_model() -> dict:
    rules = []
    for rule in _alert_rules():
        throttle = rule.get("throttle") or {}
        rules.append(
            {
                "id": rule.get("id"),
                "name": rule.get("name"),
                "severity": rule.get("severity"),
                "condition_type": (rule.get("condition") or {}).get("type", "record"),
                "channels": list(rule.get("channels") or []),
                "window_minutes": throttle.get("window_minutes"),
                "max_alerts": throttle.get("max_alerts"),
            }
        )
    return {"count": len(rules), "rules": rules}


def _estate_model() -> dict:
    return {
        "provinces": len(PROVINCES),
        "departments": len(DEPARTMENTS),
        "branches": len(BRANCHES),
        "ministries": len(MINISTRIES),
        "clusters": len(CLUSTERS),
    }


def platform_model() -> dict:
    """Return the full descriptor. Pure, cached, and free of tenant data."""
    return {
        "risk_model": _risk_model(),
        "compliance_model": _compliance_model(),
        "alert_model": _alert_model(),
        "estate": _estate_model(),
    }


def narrative_facts() -> dict:
    """Flattened view shaped for direct substitution into prose.

    Percentages are pre-rendered so a narrative author cannot accidentally
    print a raw ``0.35`` where ``35%`` was meant.
    """
    model = platform_model()
    risk = model["risk_model"]

    weights = risk["weights"]
    weight_parts = ", ".join(
        f"{risk['signal_labels'][key]} {round(weights[key] * 100)}%"
        for key in ("appscan", "imperva", "exposure", "compliance")
        if key in weights and key in risk["signal_labels"]
    )

    bands = {b["bucket"]: b["max"] for b in risk["bands"]}

    popia_domains = model["compliance_model"]["weights"]["popia"]
    iso_domains = model["compliance_model"]["weights"]["iso_27001"]

    frameworks = model["compliance_model"]["frameworks"]
    applicable = [f for f in frameworks if f["applicable"]]
    not_applicable = [f for f in frameworks if not f["applicable"]]

    return {
        "risk_weight_summary": weight_parts,
        "risk_signal_labels": risk["signal_labels"],
        "safe_max": bands["safe"],
        "monitored_max": bands["monitored"],
        "band_summary": (
            f"safe up to {bands['safe']:.0f}, "
            f"monitored up to {bands['monitored']:.0f}, "
            "critical above"
        ),
        "popia_domains": list(popia_domains),
        "popia_domain_labels": [d.replace("_", " ") for d in popia_domains],
        "iso_domain_count": len(iso_domains),
        "evidence_expiry_days": EVIDENCE_EXPIRY_DAYS,
        "owasp_taxonomy": owasp_taxonomy.taxonomy_version(),
        "owasp_categories": len(owasp_taxonomy.categories()),
        "owasp_exempt_sources": sorted(owasp_taxonomy.exempt_sources()),
        "alert_rule_count": model["alert_model"]["count"],
        "alert_rules": model["alert_model"]["rules"],
        "compliance_scores_seeded": model["compliance_model"]["scores_are_seeded"],
        "applicable_frameworks": [f["id"] for f in applicable],
        "not_applicable_frameworks": [f["id"] for f in not_applicable],
        "applicability_summary": (
            "The platform tracks an explicit applicability determination for "
            f"{len(frameworks)} instruments. {len(applicable)} are recorded as "
            f"applying or conditionally applying ({', '.join(f['id'] for f in applicable)}); "
            f"{len(not_applicable)} are recorded as assessed and not applying "
            f"({', '.join(f['id'] for f in not_applicable)})."
        ),
        **model["estate"],
    }