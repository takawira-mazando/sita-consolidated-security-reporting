"""Tests for the platform self-description endpoint.

The dashboard narrative used to be hand-authored HTML in the frontend. It
asserted the risk weights, the band thresholds, the framework domains, the
department count and the rule inventory as string literals, and none of those
literals were tested against the code they described. They drifted: the overlay
claimed 40/30/20/10 weights against an engine using 35/25/20/20, claimed 60
departments against a catalogue of 173, and claimed seven metrics were "not
tracked by the backend yet" when each had a live endpoint.

These tests pin the descriptor to the modules that actually compute. If
``risk_engine.DEFAULT_WEIGHTS`` changes, the endpoint changes with it because it
imports the constant; if someone reintroduces a hardcoded literal in the
frontend, the two disagree and these tests are the place that shows it.
"""
from __future__ import annotations

import os
import re

from app.api.narrative import narrative_facts, platform_model
from app.processing import compliance as compliance_engine
from app.processing import frameworks as framework_registry
from app.processing import risk_engine
from app.processing.risk_engine import risk_bucket

FRONTEND = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
    "src",
    "data",
    "explanations.ts",
)


class TestRiskModelMatchesEngine:
    def test_weights_are_read_from_the_engine(self):
        assert platform_model()["risk_model"]["weights"] == risk_engine.DEFAULT_WEIGHTS

    def test_band_edges_match_the_bucket_function(self):
        bands = {b["bucket"]: b["max"] for b in platform_model()["risk_model"]["bands"]}
        assert bands["safe"] == risk_engine.SAFE_MAX
        assert bands["monitored"] == risk_engine.MONITORED_MAX

    def test_band_edges_actually_produce_the_declared_buckets(self):
        """The descriptor is only useful if its edges agree with risk_bucket."""
        bands = {b["bucket"]: b["max"] for b in platform_model()["risk_model"]["bands"]}
        assert risk_bucket(bands["safe"]) == "safe"
        assert risk_bucket(bands["safe"] + 0.1) == "monitored"
        assert risk_bucket(bands["monitored"]) == "monitored"
        assert risk_bucket(bands["monitored"] + 0.1) == "critical"
        assert risk_bucket(100) == "critical"

    def test_every_weighted_signal_has_a_label(self):
        labels = platform_model()["risk_model"]["signal_labels"]
        assert set(labels) == set(risk_engine.DEFAULT_WEIGHTS)


class TestComplianceModelMatchesEngine:
    def test_domain_weights_are_read_from_the_scoring_module(self):
        weights = platform_model()["compliance_model"]["weights"]
        assert weights["popia"] == compliance_engine.POPIA_WEIGHTS
        assert weights["iso_27001"] == compliance_engine.ISO_WEIGHTS

    def test_domain_weights_sum_to_one(self):
        for framework, weights in platform_model()["compliance_model"]["weights"].items():
            assert round(sum(weights.values()), 6) == 1.0, framework

    def test_framework_registry_is_exposed_with_applicability(self):
        frameworks = platform_model()["compliance_model"]["frameworks"]
        assert {f["id"] for f in frameworks} == set(framework_registry.FRAMEWORKS)

    def test_applicability_is_not_silently_absent(self):
        """A framework that does not bind must be recorded, not omitted."""
        for framework in platform_model()["compliance_model"]["frameworks"]:
            assert framework["applicability"] in {
                "applies",
                "conditional",
                "partial",
                "not_applicable",
            }
            assert framework["rationale"], framework["id"]


class TestAlertModel:
    def test_rule_count_matches_the_shipped_yaml(self):
        import yaml

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "processing",
            "alert_rules.yaml",
        )
        with open(path) as fh:
            shipped = len(yaml.safe_load(fh).get("rules", []))
        assert platform_model()["alert_model"]["count"] == shipped
        assert shipped > 0

    def test_every_rule_carries_a_throttle_window(self):
        for rule in platform_model()["alert_model"]["rules"]:
            assert rule["id"], "a rule without an id cannot be de-duplicated"
            assert rule["window_minutes"], rule["id"]


class TestEstateModel:
    def test_counts_are_derived_from_the_tenancy_catalogue(self):
        from app.tenant import BRANCHES, CLUSTERS, DEPARTMENTS, MINISTRIES, PROVINCES

        estate = platform_model()["estate"]
        assert estate["provinces"] == len(PROVINCES)
        assert estate["departments"] == len(DEPARTMENTS)
        assert estate["branches"] == len(BRANCHES)
        assert estate["ministries"] == len(MINISTRIES)
        assert estate["clusters"] == len(CLUSTERS)

    def test_counts_are_nonzero(self):
        """A zero here is how "0 departments" language creeps back in."""
        for key, value in platform_model()["estate"].items():
            assert value > 0, key


class TestNarrativeFacts:
    def test_weight_summary_reports_percentages_not_fractions(self):
        summary = narrative_facts()["risk_weight_summary"]
        assert "35%" in summary, summary
        assert "0.35" not in summary, summary
        assert "40%" not in summary, summary

    def test_band_summary_reports_the_canonical_edges(self):
        summary = narrative_facts()["band_summary"]
        assert f"{risk_engine.SAFE_MAX:.0f}" in summary
        assert f"{risk_engine.MONITORED_MAX:.0f}" in summary

    def test_seeded_scores_are_disclosed(self):
        """compliance.overall_score is seeded; the narrative must say so."""
        assert narrative_facts()["compliance_scores_seeded"] is True

    def test_popia_domain_labels_are_human_readable(self):
        labels = narrative_facts()["popia_domain_labels"]
        assert all("_" not in label for label in labels)
        assert "cross border" in labels

    def test_descriptor_carries_no_tenant_rows(self):
        """The endpoint holds the model, not the data."""
        assert narrative_facts()["provinces"] == 9
        assert "departments" not in narrative_facts() or isinstance(
            narrative_facts()["departments"], int
        )


class TestFrontendNarrativeDoesNotRestateTheModel:
    """The regression this whole change exists to prevent.

    The narrative must not contain a numeric literal asserting a platform fact.
    Comments are stripped first: the module docstring deliberately quotes the
    old values in order to record why they were wrong, and a test that failed
    on its own explanation would be deleted with the explanation.
    """

    def _source(self) -> str:
        with open(FRONTEND, encoding="utf-8") as fh:
            raw = fh.read()
        raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)  # block comments
        raw = re.sub(r"^\s*//.*$", "", raw, flags=re.M)  # line comments
        return raw

    def test_frontend_narrative_file_exists(self):
        assert os.path.exists(FRONTEND), f"missing {FRONTEND}"

    def test_no_hardcoded_risk_weights(self):
        src = self._source()
        for weight in ("40%", "30%", "10%"):
            assert weight not in src, (
                f"explanations.ts asserts a weight of {weight}; the engine uses "
                f"{risk_engine.DEFAULT_WEIGHTS}. Weights must come from the API."
            )

    def test_no_hardcoded_department_counts(self):
        src = self._source()
        assert not re.search(r"\b\d+\s+(national\s+)?departments\b", src), (
            "explanations.ts asserts a department count; it must come from "
            "/api/v1/meta/narrative-facts"
        )

    def test_no_false_capability_claims(self):
        """Seven 'not tracked by the backend yet' notices were all false."""
        src = self._source()
        assert "not tracked by the backend yet" not in src, (
            "explanations.ts still claims a capability is absent. Each of these "
            "had a live endpoint that the same screen rendered."
        )

    def test_no_fabricated_threshold_rule(self):
        src = self._source()
        assert "fused_score &gt; 71" not in src
        assert "fused_score > 71" not in src, (
            "explanations.ts invents an alert rule that does not exist in "
            "alert_rules.yaml"
        )

    def test_cvss_is_not_asserted(self):
        """No CVSS base score is ingested anywhere in the platform.

        The old narrative claimed "CVEs with CVSS >= 7.0" on a panel that had
        no CVSS column. That claim must not come back.
        """
        src = self._source()
        assert "CVSS &ge; 7.0" not in src
        assert "CVSS ≥ 7.0" not in src

    def test_owasp_taxonomy_is_sourced_not_literal(self):
        """OWASP is now a real platform capability, so its version must come
        from the API rather than being restated as a string.

        The taxonomy edition changes when OWASP publishes a new one; a literal
        in the prose would go stale exactly like the weights did.
        """
        src = self._source()
        assert "owaspTaxonomy" in src, (
            "the narrative must read the OWASP edition from the model, not "
            "assert one"
        )
        # Outside the fallback, no bare edition year may appear in prose.
        prose = src.replace("${m.owaspTaxonomy || 'OWASP Top 10 2021'}", "")
        assert "Top 10 2021" not in prose, (
            "OWASP Top 10 2021 is stated literally outside the fallback"
        )

    def test_owasp_capability_is_real(self):
        """If the narrative claims an OWASP rollup, the endpoint must exist."""
        router = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app", "api", "routers", "metrics.py",
        )
        with open(router, encoding="utf-8") as fh:
            content = fh.read()
        assert '"/metrics/appsec/owasp"' in content, (
            "the narrative describes an OWASP panel with no endpoint behind it"
        )

    def test_compliance_scores_are_disclosed_as_seeded(self):
        src = self._source()
        assert "seeded" in src, (
            "compliance.overall_score is fixture data, not computed; the "
            "narrative must say so or it is asserting a control that does not "
            "run"
        )

    def test_every_claim_is_interpolated_not_literal(self):
        """Digits may only appear inside ${...} or as UI/standard references."""
        src = self._source()
        stripped = re.sub(r"\$\{[^}]*\}", "", src)  # drop substitutions
        stripped = re.sub(r"&[a-z]+;", "", stripped)  # drop HTML entities
        leftovers = re.findall(r"\d+", stripped)

        # Structural digits that describe the screen or cite an external
        # standard. None of them asserts a figure computed by the platform.
        # "0100" is the normalised 0-100 score range after entity stripping;
        # "27001" is the ISO/IEC standard name.
        allowed = {"0", "1", "2", "3", "4", "5", "6", "10", "100", "0100", "27001"}
        unexpected = sorted({n for n in leftovers if n not in allowed})
        assert not unexpected, (
            f"explanations.ts contains bare numeric literals {unexpected}; "
            "every platform figure must come from `facts` or `model`"
        )