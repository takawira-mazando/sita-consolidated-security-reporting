"""End-to-end tests for OWASP classification through the ingestion pipeline.

`test_owasp.py` covers the classifier in isolation. This file proves the
classification actually survives the path a real finding takes:

    OEM payload -> Normaliser -> CANONICAL_COLUMNS -> lake/writer.record_to_finding

and that the values land under tenant scoping rather than bypassing it.
"""
from __future__ import annotations

import pandas as pd
from app.lake.writer import record_to_finding
from app.processing import owasp
from app.processing.normaliser import CANONICAL_COLUMNS, Normaliser


def _frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestNormaliserAddsTheColumns:
    def test_canonical_projection_includes_owasp(self):
        for col in ("owasp_id", "cwe_id", "owasp_status", "taxonomy_version"):
            assert col in CANONICAL_COLUMNS, col

    def test_classification_runs_during_normalise(self):
        n = Normaliser()
        df = _frame([
            {
                "id": "ASC-1",
                "application_name": "payment-gateway",
                "vulnerability_name": "SQL injection",
                "description": "d",
                "owasp_category": "A03-injection",
                "first_found_date": "2026-01-01",
                "last_found_date": "2026-01-02",
                "status": "open",
            }
        ])
        out = n.normalise(df, "appscan")
        row = out.iloc[0]
        assert row["owasp_id"] == "A03"
        assert row["owasp_status"] == owasp.CLASSIFIED
        assert row["taxonomy_version"] == "owasp-top10-2021"

    def test_the_oem_category_is_preserved_untouched(self):
        """Additive, not a rewrite. Anyone working in vendor terms still can."""
        n = Normaliser()
        df = _frame([
            {
                "id": "WAF-1",
                "event_id": "WAF-1",
                "application_name": "customer-portal",
                "attack_name": "SQLi attempt",
                "request_uri": "/login",
                "attack_type": "sqli",
                "block_time": "2026-01-01T00:00:00Z",
            }
        ])
        row = n.normalise(df, "imperva_waf").iloc[0]
        assert row["category"] == "sqli"
        assert row["owasp_id"] == "A03"

    def test_compliance_rows_are_not_applicable(self):
        n = Normaliser()
        df = _frame([
            {
                "control_id": "CTRL-1",
                "framework": "popia",
                "description": "Consent management",
                "domain": "Consent",
                "due_date": "2026-06-01",
                "status": "open",
            }
        ])
        row = n.normalise(df, "compliance").iloc[0]
        assert row["owasp_status"] == owasp.NOT_APPLICABLE
        assert row["owasp_id"] is None


class TestWriterBoundary:
    """A caller that bypasses the Normaliser must not be able to invent an id."""

    def test_writer_classifies_when_the_normaliser_did_not(self):
        finding = record_to_finding(
            {"external_id": "X-1", "app_name": "legacy-api", "title": "t",
             "category": "brute-force", "severity": "high"},
            "imperva_waf",
        )
        assert finding["owasp_id"] == "A07"
        assert finding["owasp_status"] == owasp.CLASSIFIED

    def test_writer_rejects_an_owasp_id_the_registry_does_not_know(self):
        finding = record_to_finding(
            {"external_id": "X-2", "app_name": "legacy-api", "title": "t",
             "category": "A99-invented-category", "severity": "high"},
            "appscan",
        )
        assert finding["owasp_id"] is None
        assert finding["owasp_status"] == owasp.UNMAPPED

    def test_writer_derives_from_source_not_from_a_supplied_owasp_id(self):
        """An injected owasp_id in the payload is ignored, not trusted."""
        finding = record_to_finding(
            {"external_id": "X-3", "app_name": "legacy-api", "title": "t",
             "category": "sqli", "owasp_id": "A01", "severity": "high"},
            "imperva_waf",
        )
        assert finding["owasp_id"] == "A03"

    def test_fallback_key_chain_is_respected(self):
        """`attack_type` reaches the column when `category` is absent."""
        finding = record_to_finding(
            {"external_id": "X-4", "app_name": "legacy-api", "title": "t",
             "attack_type": "shadow_api", "severity": "medium"},
            "apisec",
        )
        assert finding["category"] == "shadow_api"
        assert finding["owasp_id"] == "A05"


class TestCrossSourceAgreement:
    """The claim the whole feature makes: one taxonomy across every source."""

    def test_the_same_defect_from_three_tools_lands_in_one_category(self):
        """An injection seen by AppScan, Imperva WAF and Imperva DAM."""
        results = [
            record_to_finding(
                {"external_id": "A", "app_name": "payment-gateway", "title": "t",
                 "category": "A03-injection", "severity": "high"}, "appscan"),
            record_to_finding(
                {"external_id": "W", "app_name": "payment-gateway", "title": "t",
                 "category": "sqli", "severity": "high"}, "imperva_waf"),
            record_to_finding(
                {"external_id": "D", "app_name": "payment-gateway", "title": "t",
                 "category": "sql_injection", "severity": "high"}, "imperva_dam"),
        ]
        assert {r["owasp_id"] for r in results} == {"A03"}

    def test_three_different_defects_stay_apart(self):
        results = [
            record_to_finding(
                {"external_id": "1", "app_name": "a", "title": "t",
                 "category": "idor", "severity": "high"}, "appscan"),
            record_to_finding(
                {"external_id": "2", "app_name": "a", "title": "t",
                 "category": "brute-force", "severity": "high"}, "imperva_waf"),
            record_to_finding(
                {"external_id": "3", "app_name": "a", "title": "t",
                 "category": "rate_limit", "severity": "medium"}, "apisec"),
        ]
        assert {r["owasp_id"] for r in results} == {"A01", "A07", "A04"}


class TestScopeIsUnaffected:
    def test_classification_does_not_add_a_tenancy_column(self):
        """Tenancy stays denormalised at write time exactly as before."""
        keys = set(record_to_finding({"external_id": "S-1", "title": "t"}, "appscan"))
        for col in ("department_id", "branch_id", "ministry_id", "cluster_id"):
            assert col in keys, col
        for col in ("owasp_id", "cwe_id", "owasp_status", "taxonomy_version"):
            assert col in keys, col
