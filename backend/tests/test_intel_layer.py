"""Tests for the deterministic intelligence layer.

The central claim these tests defend is the one the layer exists to make:
**the platform's intelligence capability does not depend on a model.** Nothing
here mocks a model, and nothing here needs one. If a future change puts a
deterministic computation behind an AI gate, these tests keep passing ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â so the
guard has to be explicit, and :class:`TestCapabilityBoundary` is it.
"""
from __future__ import annotations

import pytest
from app.processing.compliance import ISO_WEIGHTS, POPIA_WEIGHTS
from app.processing.intel import capability, controls
from app.processing.intel.controls import CATALOGUE, SCORERS
from app.processing.intel.delta import decompose
from app.processing.intel.estate import Finding_
from app.processing.intel.privilege import (
    SEPARATION_OF_DUTIES,
    _detail_of,
    _roles_of,
    separation_of_duties_conflicts,
)
from app.processing.intel.vendor import Check


def _avp_order(avp: str) -> int:
    """Numeric sort. Plain string sort puts AVP-10 before AVP-2."""
    return int(avp.split("-")[1])


class TestCapabilityBoundary:
    """The registry is the architectural statement; these pin it down."""

    def test_every_proposition_is_registered(self):
        assert len(capability.REGISTRY) == 12
        assert sorted(capability.REGISTRY, key=_avp_order) == [
            f"AVP-{n}" for n in range(1, 13)
        ]

    def test_only_three_gates_are_permitted(self):
        for prop in capability.REGISTRY.values():
            for part in prop.parts:
                assert part.reason in capability.REASONS, (
                    f"{prop.avp}/{part.name} declares an undeclared reason {part.reason!r}. "
                    "If a new gate is genuinely needed it must be added to REASONS "
                    "and argued for, not invented locally."
                )

    def test_four_propositions_have_ai_residue(self):
        """Five of twelve carry an irreducible deliverable.

        The bar is strict: a deliverable a Jinja template can emit is not AI,
        however much prose it contains. AVP-7's prescription and AVP-9's hunt
        narrative both failed that bar and were demoted to engineering."""
        with_residue = sorted(
            (a for a, p in capability.REGISTRY.items() if p.residue),
            key=_avp_order,
        )
        assert with_residue == ["AVP-2", "AVP-3", "AVP-5", "AVP-8", "AVP-11"]

    def test_seven_are_demoted_to_the_engineering_backlog(self):
        demoted = sorted(
            (a for a, p in capability.REGISTRY.items() if not p.residue),
            key=_avp_order,
        )
        assert demoted == [
            "AVP-1", "AVP-4", "AVP-6", "AVP-7",
            "AVP-9", "AVP-10", "AVP-12",
        ]

    def test_every_demotion_states_its_reason(self):
        for avp, reason in capability.demoted().items():
            assert reason.strip(), f"{avp} was demoted without saying why"

    def test_every_residue_states_its_gate(self):
        for avp, prop in capability.REGISTRY.items():
            if prop.residue:
                assert prop.residue_gate, f"{avp} has a residue but no gate"
                assert prop.residue_gate in capability.REASONS

    def test_a_residue_is_a_capability_not_a_specification(self):
        """If the residue reads like a work order, the reduction has not happened."""
        for avp, prop in capability.REGISTRY.items():
            assert len(prop.residue) < 400, (
                f"{avp} residue is {len(prop.residue)} chars ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â that reads like a "
                "specification, not an irreducible capability"
            )

    def test_avp1_needs_no_model(self):
        """Scoring arithmetic was already written and never called.

        The platform shipped POPIA_WEIGHTS, ISO_WEIGHTS and compute_framework_score
        with zero callers, which is why compliance_snapshots holds fixture numbers.
        The fix is to call the engine, not to outsource it.
        """
        assert not capability.requires_model("AVP-1")
        assert not capability.get("AVP-1").residue

    def test_gates_are_only_the_three_legitimate_reasons(self):
        """Nothing may claim a gate for a reason outside the three."""
        for avp, prop in capability.REGISTRY.items():
            for part in prop.gated_parts:
                assert part.reason in (
                    capability.DETECTION_CONTENT,
                    capability.THREAT_ENRICHMENT,
                    capability.LEGAL_GUIDANCE,
                ), f"{avp}/{part.name} gated on {part.reason}"

    def test_every_gated_part_states_what_it_is_blocked_on(self):
        for avp, prop in capability.REGISTRY.items():
            for part in prop.gated_parts:
                assert part.blocked_on, (
                    f"{avp}/{part.name} is gated but does not say why. A gate "
                    "without a stated reason becomes an assumption."
                )

    def test_unknown_proposition_raises(self):
        with pytest.raises(KeyError):
            capability.get("AVP-99")

    def test_manifest_reports_counts_consistently(self):
        m = capability.manifest()
        assert m["proposition_count"] == len(capability.REGISTRY)
        assert m["requires_model_count"] == sum(
            1 for p in capability.REGISTRY.values() if p.requires_model
        )
        assert len(m["propositions"]) == len(capability.REGISTRY)


class TestShippedParts:
    """Anything marked shipped must name a real module."""

    def test_every_shipped_part_names_a_module(self):
        for avp, parts in capability.shipped_parts().items():
            for part in parts:
                assert part.implemented_in, (
                    f"{avp}/{part.name} is marked shipped but names no module"
                )

    def test_shipped_parts_all_exist_on_disk(self):
        """A shipped part must resolve to a real module, or a real data file.

        Curated mappings are YAML, not Python, so a shipped part may legitimately
        point at attack_mapping.yaml. Both are checked; neither is assumed, and
        the dotted ``implemented_in`` form is converted for the filesystem case.
        """
        import importlib
        import os

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for avp, parts in capability.shipped_parts().items():
            for part in parts:
                if part.implemented_in.endswith((".yaml", ".yml", ".json")):
                    stem, ext = os.path.splitext(part.implemented_in)
                    # Only the module-path dots become separators; the
                    # extension's dot must survive.
                    path = os.path.join(root, stem.replace(".", os.sep) + ext)
                    assert os.path.isfile(path), (
                        f"{avp}/{part.name}: data file {part.implemented_in} "
                        f"missing (looked in {path})"
                    )
                else:
                    module = importlib.import_module(part.implemented_in)
                    assert module is not None, (
                        f"{avp}/{part.name}: {part.implemented_in} missing"
                    )

    def test_a_shipped_part_is_never_gated(self):
        for avp, parts in capability.shipped_parts().items():
            for part in parts:
                assert part.reason == capability.DETERMINISTIC


class TestDecompose:
    """AVP-8 stage (a). Pure arithmetic, so it is fully pinned."""

    def test_single_signal_dominates(self):
        out = decompose(5.9, {
            "appscan": 5.9, "imperva": 0.6,
            "api_exposure": -0.1, "compliance_penalty": 0.0,
        })
        assert out[0].signal == "appscan"
        assert out[0].delta == 5.9
        # Share is of total absolute movement (6.6), not net (6.4), so that
        # shares always total 100 and never turn negative.
        assert out[0].share_pct == pytest.approx(89.4, abs=0.1)

    def test_signals_ordered_by_absolute_movement(self):
        out = decompose(0.0, {
            "appscan": 1.0, "imperva": -4.0,
            "api_exposure": 2.0, "compliance_penalty": 0.5,
        })
        assert [c.signal for c in out] == [
            "imperva", "api_exposure", "appscan", "compliance_penalty",
        ]

    def test_negative_contributor_gets_positive_share(self):
        """A signal that moved down must not read as a negative percentage."""
        out = decompose(-2.0, {
            "appscan": -2.0, "imperva": 0.0,
            "api_exposure": 0.0, "compliance_penalty": 0.0,
        })
        assert out[0].delta == -2.0
        assert out[0].share_pct == 100.0
        assert out[0].share_pct > 0

    def test_shares_sum_to_one_hundred(self):
        out = decompose(3.0, {
            "appscan": 1.0, "imperva": 1.0,
            "api_exposure": 1.0, "compliance_penalty": 0.0,
        })
        assert round(sum(c.share_pct for c in out), 0) == 100

    def test_no_movement_yields_zero_shares_not_a_crash(self):
        out = decompose(0.0, {
            "appscan": 0.0, "imperva": 0.0,
            "api_exposure": 0.0, "compliance_penalty": 0.0,
        })
        assert all(c.share_pct == 0.0 for c in out)
        assert sum(c.delta for c in out) == 0.0

    def test_all_four_signals_always_reported(self):
        """A signal that did not move must still be visible as zero."""
        out = decompose(1.0, {"appscan": 1.0})
        assert {c.signal for c in out} == {
            "appscan", "imperva", "api_exposure", "compliance_penalty",
        }

    def test_missing_signal_defaults_to_zero(self):
        out = decompose(1.0, {"appscan": 1.0, "imperva": None})
        imperva = next(c for c in out if c.signal == "imperva")
        assert imperva.delta == 0.0


class TestCheckSerialisation:
    def test_detail_defaults_to_empty_list(self):
        c = Check(id="x", finding="y", count=0)
        assert c.as_dict()["detail"] == []

    def test_count_is_reported_alongside_detail(self):
        """Total and sample are separate: a truncated detail must not read as total."""
        c = Check(id="x", finding="y", count=412, detail=[{"a": 1}])
        d = c.as_dict()
        assert d["count"] == 412
        assert len(d["detail"]) == 1


class TestEstateFindingSerialisation:
    def test_detail_defaults_to_empty_list(self):
        assert Finding_(id="x", finding="y", count=0).as_dict()["detail"] == []


class TestRoleAndPayloadParsing:
    """``record_access`` writes actor_role comma-joined and signed_payload as JSON."""

    class _Row:
        def __init__(self, actor_role=None, signed_payload=None):
            self.actor_role = actor_role
            self.signed_payload = signed_payload

    def test_roles_split_on_comma(self):
        assert _roles_of(self._Row("compliance,soc")) == ["compliance", "soc"]

    def test_roles_tolerate_whitespace(self):
        assert _roles_of(self._Row(" admin , exec ")) == ["admin", "exec"]

    def test_roles_of_null_is_empty(self):
        assert _roles_of(self._Row(None)) == []

    def test_detail_recovered_from_signed_payload(self):
        row = self._Row(signed_payload='{"detail": {"row_count": 1200, "dataset": "findings"}}')
        assert _detail_of(row) == {"row_count": 1200, "dataset": "findings"}

    def test_unsigned_row_yields_empty_detail_not_an_exception(self):
        assert _detail_of(self._Row(signed_payload=None)) == {}
        assert _detail_of(self._Row(signed_payload="not json")) == {}

    def test_payload_with_no_detail_key(self):
        assert _detail_of(self._Row(signed_payload='{"action": "x"}')) == {}


class TestSeparationOfDuties:
    def test_every_pair_is_actually_exclusive(self):
        for pair in SEPARATION_OF_DUTIES:
            assert len(pair) == 2

    def test_pairs_are_distinct(self):
        assert len(SEPARATION_OF_DUTIES) == len(set(SEPARATION_OF_DUTIES))

    def test_declared_conflicts_are_readable(self):
        conflicts = separation_of_duties_conflicts()
        assert len(conflicts) == len(SEPARATION_OF_DUTIES)
        for c in conflicts:
            assert len(c["roles"]) == 2
            assert c["rationale"]

    def test_admin_and_compliance_is_a_defined_conflict(self):
        assert frozenset({"admin", "compliance"}) in SEPARATION_OF_DUTIES


class TestControlCatalogue:
    """AVP-1. The point of these is that the score is computed, not seeded."""

    def test_every_popia_condition_is_catalogued(self):

        domains = {c.domain for c in CATALOGUE}
        assert domains == set(POPIA_WEIGHTS), "catalogue must cover every weighted domain"

    def test_catalogue_weights_match_the_engine(self):

        for c in CATALOGUE:
            assert c.weight == POPIA_WEIGHTS[c.domain]

    def test_weights_still_sum_to_one(self):

        assert round(sum(POPIA_WEIGHTS.values()), 6) == 1.0

    def test_control_without_evidence_says_why(self):
        """A condition with no binding must state the reason, never score silently."""
        for c in CATALOGUE:
            if c.evidence is None:
                assert c.no_evidence_reason, f"{c.control_id} has no evidence and no reason"

    def test_every_evidence_key_has_a_function_and_a_scorer(self):
        for c in CATALOGUE:
            if c.evidence is None:
                continue
            assert c.evidence in controls.EVIDENCE, f"{c.control_id}: {c.evidence}"
            assert c.evidence in SCORERS, f"{c.control_id}: {c.evidence}"

    def test_scorer_never_divides_by_zero(self):
        for name, scorer in SCORERS.items():
            assert scorer({}) == 0.0, f"{name} must score 0 on empty evidence"

    def test_computed_score_uses_the_existing_engine(self):
        """Not a reimplementation. The platform already owns this arithmetic."""
        from app.processing.compliance import compute_framework_score

        got = compute_framework_score({"security_safeguards": 100.0}, POPIA_WEIGHTS)
        assert got == 30.0

    def test_iso_publishes_no_score_despite_partial_bindings(self):
        """Four themes bound, eight not. Still no score.

        A score from 4 of 12 Annex A themes overstates coverage in the one
        direction an auditor cares about. The bound/unbound split is returned
        instead, which makes the remaining work legible."""
        status = controls.iso_status()
        assert status["score"] is None
        assert status["computed"] is False
        assert status["requires_model"] is False
        assert 0 < status["themes_with_evidence_binding"] < status["themes_total"]
        assert len(status["themes_bound"]) == status["themes_with_evidence_binding"]
        assert len(status["themes_unbound"]) == (
            status["themes_total"] - status["themes_with_evidence_binding"]
        )

    def test_every_iso_binding_resolves_to_a_real_evidence_function(self):
        for theme, (key, why) in controls.ISO_BINDINGS.items():
            assert theme in ISO_WEIGHTS, f"{theme} is not an Annex A theme"
            assert why, f"{theme} has no stated reason"
            if key is not None:
                assert key in controls.EVIDENCE, f"{theme}: no evidence fn {key}"
                assert key in controls.SCORERS, f"{theme}: no scorer {key}"

    def test_iso_bindings_cover_exactly_the_weighted_themes(self):
        assert set(controls.ISO_BINDINGS) == set(ISO_WEIGHTS)

    def test_iso_weights_still_sum_to_one(self):
        assert round(sum(ISO_WEIGHTS.values()), 6) == 1.0



class TestNoModelImports:
    """The layer must not reach for an AI dependency.

    A structural assertion rather than a behavioural one: if a future change adds
    an httpx call or an inference import to any module here, this fails even
    though every other test would still pass.
    """

    MODULES = (
        "app.processing.intel.capability",
        "app.processing.intel.controls",
        "app.processing.intel.delta",
        "app.processing.intel.estate",
        "app.processing.intel.privilege",
        "app.processing.intel.vendor",
    )

    FORBIDDEN = (
        "ollama", "openai", "anthropic", "transformers", "langchain",
        "llama_index", "httpx", "requests", "aiohttp",
    )

    @pytest.mark.parametrize("module", MODULES)
    def test_module_does_not_import_an_ai_or_http_dependency(self, module):
        import ast
        import importlib
        import inspect

        mod = importlib.import_module(module)
        tree = ast.parse(inspect.getsource(mod))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
        offenders = imported & set(self.FORBIDDEN)
        assert not offenders, (
            f"{module} imports {sorted(offenders)}. The deterministic layer must "
            "reach no model and no network; that property is what makes it "
            "testable with AI switched off and safe to sign."
        )