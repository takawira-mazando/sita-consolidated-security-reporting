"""Tests for OWASP Top 10 classification.

The problem this guards against is specific: `warehouse.findings.category` is a
verbatim pass-through of each OEM's own taxonomy, so before this existed a
`GROUP BY category` across the estate grouped AppScan's ``A03-injection`` with
Imperva's ``sqli`` and a POPIA ``Consent`` domain in the same bucket.

The three properties worth protecting are:
  1. a vendor value maps to the right category,
  2. an unmapped value stays *unmapped* rather than being guessed, and
  3. a source whose vocabulary is not a vulnerability class is never forced
     into A01-A10.
"""
from __future__ import annotations

import os

import yaml
from app.processing import owasp
from app.processing.owasp import (
    ABSENT,
    CLASSIFIED,
    NOT_APPLICABLE,
    UNMAPPED,
    classify,
)


class TestRegistry:
    def test_ten_categories_are_defined(self):
        assert len(owasp.categories()) == 10

    def test_ids_are_a01_through_a10(self):
        assert sorted(owasp.categories()) == [f"A{n:02d}" for n in range(1, 11)]

    def test_every_category_has_a_name_and_a_summary(self):
        for cid, cat in owasp.categories().items():
            assert cat.name, cid
            assert cat.summary, cid

    def test_taxonomy_version_is_pinned(self):
        assert owasp.taxonomy_version() == "owasp-top10-2021"

    def test_registry_is_exposed_for_the_api(self):
        rows = owasp.as_dicts()
        assert len(rows) == 10
        assert rows[0]["taxonomy_version"] == "owasp-top10-2021"


class TestAlreadyCanonicalValues:
    def test_slugs_pass_through(self):
        for value, expected in [
            ("A01-broken-access-control", "A01"),
            ("A03-injection", "A03"),
            ("A07-identification-auth-failures", "A07"),
            ("A10-ssrf", "A10"),
        ]:
            assert classify(value, "appscan").owasp_id == expected

    def test_year_stamped_ids_pass_through(self):
        assert classify("A03:2021", "appscan").owasp_id == "A03"

    def test_owasp_names_pass_through(self):
        assert classify("Broken Access Control", "appscan").owasp_id == "A01"
        assert classify("Software Integrity Failures", "appscan").owasp_id == "A08"


class TestCrossSourceMapping:
    """The whole point: different vendors, one taxonomy."""

    def test_imperva_waf_attack_types(self):
        for value, expected in [
            ("sqli", "A03"),
            ("xss", "A03"),
            ("rce", "A03"),
            ("lfi", "A03"),
            ("shellshock", "A03"),
            ("brute-force", "A07"),
        ]:
            result = classify(value, "imperva_waf")
            assert result.owasp_id == expected, f"{value} -> {result.owasp_id}"
            assert result.status == CLASSIFIED

    def test_imperva_dam_violation_types(self):
        for value, expected in [
            ("unauth_access", "A01"),
            ("privilege_abuse", "A01"),
            ("data_exfil", "A01"),
            ("sql_injection", "A03"),
        ]:
            assert classify(value, "imperva_dam").owasp_id == expected, value

    def test_api_security_issue_types(self):
        for value, expected in [
            ("auth_missing", "A07"),
            ("data_overexposure", "A01"),
            ("rate_limit", "A04"),
            ("shadow_api", "A05"),
        ]:
            assert classify(value, "apisec").owasp_id == expected, value

    def test_the_same_word_maps_differently_per_source_when_it_should(self):
        """`sqli` is injection; `brute-force` is an authentication failure."""
        assert classify("sqli", "imperva_waf").owasp_id == "A03"
        assert classify("brute-force", "imperva_waf").owasp_id == "A07"

    def test_source_prefix_resolution_matches_the_normaliser(self):
        """`appscan_real` must resolve the same way `appscan` does."""
        assert classify("sqli", "appscan").owasp_id == "A03"
        assert classify("sqli", "appscan_real").owasp_id == "A03"


class TestCwe:
    def test_cwe_is_preserved_alongside_the_owasp_id(self):
        result = classify("CWE-89", "appscan")
        assert result.owasp_id == "A03"
        assert result.cwe_id == "CWE-89"

    def test_common_cwe_identifiers(self):
        for cwe, expected in [
            ("CWE-79", "A03"),    # XSS
            ("CWE-22", "A01"),    # path traversal
            ("CWE-918", "A10"),   # SSRF
            ("CWE-287", "A07"),   # improper authentication
            ("CWE-502", "A08"),   # deserialisation
            ("CWE-798", "A07"),   # hardcoded credentials
            ("CWE-1104", "A06"),  # unmaintained components
        ]:
            assert classify(cwe, "appscan").owasp_id == expected, cwe

    def test_lowercase_and_padded_cwe_forms_are_accepted(self):
        for value in ("cwe-89", "CWE_89", "cwe 89"):
            assert classify(value, "appscan").owasp_id == "A03", value

    def test_unknown_cwe_is_unmapped_not_guessed(self):
        result = classify("CWE-99999", "appscan")
        assert result.owasp_id is None
        assert result.cwe_id == "CWE-99999"
        assert result.status == UNMAPPED


class TestRefusesToGuess:
    """A wrong OWASP id in an assurance artefact is worse than an admitted gap."""

    def test_unknown_value_is_unmapped(self):
        result = classify("totally-unknown", "appscan")
        assert result.owasp_id is None
        assert result.status == UNMAPPED

    def test_unmapped_records_the_value_and_source_for_curation(self):
        result = classify("brand_new_attack", "imperva_waf")
        assert result.reason
        assert "brand_new_attack" in result.reason
        assert "imperva_waf" in result.reason

    def test_unmapped_still_carries_the_taxonomy_version(self):
        assert classify("unknown", "appscan").taxonomy_version == "owasp-top10-2021"

    def test_reconnaissance_noise_is_not_forced_into_a_category(self):
        """`scanner-probe` is an observation, not a weakness class."""
        assert classify("scanner-probe", "imperva_waf").owasp_id is None

    def test_vendor_placeholders_stay_unmapped(self):
        for value in ("policy_other", "anomaly", "other"):
            assert classify(value, "imperva_dam").status == UNMAPPED, value


class TestExemptSources:
    def test_compliance_is_not_applicable(self):
        for domain in ("Consent", "Breach Response", "Cross-Border", "Data Inventory"):
            result = classify(domain, "compliance")
            assert result.owasp_id is None
            assert result.status == NOT_APPLICABLE, domain

    def test_exempt_state_is_distinguishable_from_unmapped(self):
        assert classify("Consent", "compliance").status != classify("Consent", "appscan").status

    def test_sql_statement_types_are_unmapped_not_wrong(self):
        """A DAM statement type is an operation, not a weakness."""
        for value in ("READ", "WRITE", "QUERY", "ADMIN"):
            assert classify(value, "thales").owasp_id is None, value


class TestAbsentValues:
    def test_none_is_absent(self):
        assert classify(None, "appscan").status == ABSENT

    def test_empty_and_nan_are_absent(self):
        for value in ("", "   ", "nan", "NaN", "none", "None"):
            assert classify(value, "appscan").status == ABSENT, repr(value)

    def test_absent_is_distinguishable_from_unmapped(self):
        assert classify(None, "appscan").status != classify("weird", "appscan").status


class TestMappingFileHygiene:
    """The mapping is configuration a reviewer reads, so it has to stay clean."""

    @staticmethod
    def _raw() -> dict:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "processing",
            "owasp_mapping.yaml",
        )
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def test_every_rule_targets_a_real_category(self):
        raw = self._raw()
        valid = {str(k).upper() for k in raw["categories"]}
        for source, mapping in raw["rules"].items():
            for vendor_value, target in mapping.items():
                assert str(target).upper() in valid, f"{source}.{vendor_value} -> {target}"

    def test_every_cwe_targets_a_real_category(self):
        raw = self._raw()
        valid = {str(k).upper() for k in raw["categories"]}
        for cwe, target in raw["cwe"].items():
            assert str(target).upper() in valid, f"CWE-{cwe} -> {target}"

    def test_mapping_keys_are_normalisable(self):
        """Lookup lowercases both sides; a mixed-case key would silently miss."""
        raw = self._raw()
        for mapping in list(raw["rules"].values()) + [raw["cwe"]]:
            for key in mapping:
                assert key == str(key).strip().lower() or str(key).isdigit(), repr(key)

    def test_no_duplicate_keys_silently_swallowed_by_yaml(self):
        """PyYAML keeps the last value for a repeated key.

        A duplicate therefore looks applied in review while the value actually in
        force is the one nobody read. Detect it by refusing to load.
        """
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "app",
            "processing",
            "owasp_mapping.yaml",
        )
        seen: dict[str, str] = {}

        class StrictLoader(yaml.SafeLoader):
            pass

        def _no_duplicates(loader, node, deep=False):
            mapping = {}
            for key_node, value_node in node.value:
                key = loader.construct_object(key_node, deep=deep)
                if key in mapping:
                    seen.setdefault(str(key), node.start_mark.line + 1)
                    seen[str(key)] = node.start_mark.line + 1
                mapping[key] = loader.construct_object(value_node, deep=deep)
            return mapping

        StrictLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates
        )
        with open(path, encoding="utf-8") as fh:
            yaml.load(fh, Loader=StrictLoader)
        assert not seen, f"duplicate mapping keys at lines {seen}"

    def test_every_owasp_category_has_at_least_one_cwe(self):
        """A category with no CWE coverage is a gap in the table, not in the data."""
        raw = self._raw()
        covered = {str(v).upper() for v in raw["cwe"].values()}
        missing = sorted(set(k.upper() for k in raw["categories"]) - covered)
        assert not missing, f"OWASP categories with no CWE mapping: {missing}"

    def test_exempt_sources_are_declared_not_hardcoded_in_logic(self):
        raw = self._raw()
        assert "compliance" in raw["exempt_sources"]
        assert owasp.exempt_sources() == {"compliance"}


class TestClassificationIsDeterministic:
    def test_same_input_gives_same_output(self):
        for value, source in [
            ("sqli", "imperva_waf"),
            ("CWE-89", "appscan"),
            ("Consent", "compliance"),
            ("mystery", "apisec"),
        ]:
            first = classify(value, source)
            second = classify(value, source)
            assert first == second

    def test_classified_flag_agrees_with_the_id(self):
        for value, source in [("sqli", "imperva_waf"), ("unknown", "apisec")]:
            assert classify(value, source).classified == (classify(value, source).owasp_id is not None)

    def test_statuses_are_from_the_declared_vocabulary(self):
        for value, source in [("sqli", "imperva_waf"), (None, "appscan"), ("x", "compliance")]:
            assert classify(value, source).status in owasp.known_statuses()
