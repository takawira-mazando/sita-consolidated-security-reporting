"""Which capability requires a model, and which does not.

Why this module exists
----------------------
Twelve value propositions were written against this platform, then audited
against the live schema (``docs/AIMI_INTELLIGENCE_VALUE_PROPOSITIONS.md`` §6.1)
and then reduced to their irreducible residue (§6.3). Both passes removed work.

The audit found that most propositions assumed data the platform does not hold.
The residue pass found that most of what remained was arithmetic the platform
already owns — and in two cases, prose a Jinja template could emit.

The rule this module encodes
---------------------------
**Assembly, detection, scoring, correlation, comparison and signing are
deterministic. Only the residue below needs a model.**

``residue`` is deliberately a stricter bar than "involves prose" or "is
generative". A deliverable that a template can produce is not AI, however much
English it contains. Nine propositions failed that bar and now carry an empty
residue, which drops them from any AI business case and returns them to the
engineering backlog where they belong.

The four survivors
------------------
- **AVP-2** Authoring a working detection rule. The mapping from a technique to
  a logsource to a field predicate is authored, not looked up.
- **AVP-3** Attributing an observed campaign to *this* estate. Reading threat
  reporting and judging whether it names this sector and this technique set.
- **AVP-5** Applying a statutory test to technical facts. Deciding whether a
  given incident meets the POPIA s.22 threshold is a legal judgement.
- **AVP-11** Explaining a behavioural sequence across many audit rows. Each row
  is a query; the pattern across them is not.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: The reasons a part may be held behind a gate. Used for part-level
#: classification; the proposition-level test is ``Proposition.residue``.
DETERMINISTIC = "deterministic"
DETECTION_CONTENT = "detection_content"
THREAT_ENRICHMENT = "threat_enrichment"
LEGAL_GUIDANCE = "legal_guidance"

REASONS = frozenset({DETERMINISTIC, DETECTION_CONTENT, THREAT_ENRICHMENT, LEGAL_GUIDANCE})


@dataclass(frozen=True)
class Part:
    """One deliverable within a proposition."""

    name: str
    reason: str
    implemented_in: str = ""
    shipped: bool = False
    blocked_on: str = ""


@dataclass(frozen=True)
class Proposition:
    avp: str
    title: str
    parts: tuple[Part, ...] = field(default_factory=tuple)
    #: The one deliverable impossible without a model. Empty means no AI residue.
    residue: str = ""
    residue_gate: str = ""
    #: Why this proposition has no AI residue, when it has none.
    demoted_because: str = ""

    @property
    def deterministic_parts(self) -> tuple[Part, ...]:
        return tuple(p for p in self.parts if p.reason == DETERMINISTIC)

    @property
    def gated_parts(self) -> tuple[Part, ...]:
        return tuple(p for p in self.parts if p.reason != DETERMINISTIC)

    @property
    def requires_model(self) -> bool:
        """True only where a genuinely irreducible deliverable exists."""
        return bool(self.residue)


REGISTRY: dict[str, Proposition] = {
    p.avp: p
    for p in (
        Proposition(
            avp="AVP-1",
            title="Control scoring and evidence-bound compliance",
            parts=(
                Part("control_catalogue", DETERMINISTIC, "app.processing.intel.controls", True),
                Part("evidence_binding", DETERMINISTIC, "app.processing.intel.controls", True),
                Part("score_recomputation", DETERMINISTIC, "app.processing.intel.controls", True),
                Part("iso_scoring", DETERMINISTIC, "app.processing.intel.controls", True,
                     "four Annex A themes now bound; still publishes no score "
                     "because 8 of 12 are unbound"),
            ),
            demoted_because=(
                "The scoring engine already existed with zero callers. Binding a "
                "control to an observable is a join, and summing weighted domain "
                "percentages is arithmetic. Written a Catalogue Draft for Compliance "
                "to sign; the legal knowledge that goes into it is a human reading "
                "SAFLII offline, not a runtime model."
            ),
        ),
        Proposition(
            avp="AVP-2",
            title="ATT&CK coverage and detection content",
            parts=(
                Part("cwe_to_technique_map", DETERMINISTIC,
                     "app.processing.intel.attack_mapping.yaml", True),
                Part("red_blue_coverage", DETERMINISTIC, "app.processing.intel.attack", True),
                Part("heatmap_layer", DETERMINISTIC, "app.processing.intel.attack", True),
                Part("rule_diff_presentation", DETERMINISTIC, "app.processing.intel.attack", True,
                     "text operation against a file the client already reviews"),
            ),
            residue=(
                "Author an alerting rule for received telemetry: given an attacker "
                "technique, decide which OEM source and which normalised field "
                "evidences it, choose the predicate and threshold, and emit a rule "
                "in the platform's own alert_rules.yaml shape."
            ),
            residue_gate=DETECTION_CONTENT,
        ),
        Proposition(
            avp="AVP-3",
            title="Threat-context signal on the risk model",
            parts=(
                Part("cve_id_column", DETERMINISTIC, "", False,
                     "half a day; the connector already receives cve"),
                Part("signal_weighting", DETERMINISTIC,
                     "app.processing.risk_engine", False),
                Part("pulse_count_lookup", DETERMINISTIC, "", False,
                     "an OTX lookup is an API call, not a model"),
            ),
            residue=(
                "Attribute an observed campaign to this estate: read threat "
                "reporting, judge whether it names this target sector, and map its "
                "technique set onto the techniques this estate is exposed to."
            ),
            residue_gate=THREAT_ENRICHMENT,
        ),
        Proposition(
            avp="AVP-4",
            title="Cross-OEM contradiction detection",
            parts=(
                Part("single_vendor_apps", DETERMINISTIC, "app.processing.intel.vendor", True),
                Part("vendor_agreement_matrix", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("endpoints_never_attacked", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("ageing_asymmetry", DETERMINISTIC, "app.processing.intel.vendor", True),
                Part("appname_normalisation_quality", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("app_to_database_mapping", DETERMINISTIC, "", False,
                     "findings.app_name and database_inventory.name are different "
                     "namespaces; no mapping table exists"),
            ),
            demoted_because=(
                "Every check is a GROUP BY or a set difference over columns the "
                "warehouse already carries. Five of six are built and live."
            ),
        ),
        Proposition(
            avp="AVP-5",
            title="POPIA s.22 breach-notification readiness",
            parts=(
                Part("evidence_chain_assembly", DETERMINISTIC, "", False),
                Part("packet_signing", DETERMINISTIC, "app.security_pki", False),
                Part("packet_rendering", DETERMINISTIC, "", False,
                     "jinja2 is already a dependency"),
                Part("s22_threshold_judgement", LEGAL_GUIDANCE, "", False,
                     "applying a statutory test to technical facts is a legal "
                     "judgement; no rule encodes when a compromise is severe enough"),
                Part("notification_narrative", LEGAL_GUIDANCE, "", False,
                     "drafted from the assembled evidence, but must state the "
                     "regulator-facing case in prose and be approved by a person"),
            ),
            residue=(
                "Apply the POPIA s.22 statutory test to a specific set of technical "
                "facts and decide whether the notification duty is triggered, then "
                "draft the notification narrative for a human to approve."
            ),
            residue_gate=LEGAL_GUIDANCE,
        ),
        Proposition(
            avp="AVP-6",
            title="Estate ownership and concentration graph",
            parts=(
                Part("ambiguous_ownership", DETERMINISTIC, "app.processing.intel.estate", True),
                Part("shared_application_blast_radius", DETERMINISTIC,
                     "app.processing.intel.estate", True),
                Part("ministry_cluster_conflict", DETERMINISTIC,
                     "app.processing.intel.estate", True),
                Part("monitoring_asymmetry", DETERMINISTIC, "app.processing.intel.estate", True),
            ),
            demoted_because=(
                "COUNT(DISTINCT ...) > 1 over six columns already denormalised onto "
                "every warehouse row. Built and live. No vector store, no embedding, "
                "no graph inference."
            ),
        ),
        Proposition(
            avp="AVP-7",
            title="Prescriptive peer contrast",
            parts=(
                Part("peer_ranking", DETERMINISTIC,
                     "app.api.routers.benchmark", True),
                Part("control_gap_prescription", DETERMINISTIC, "app.processing.intel.peer", True,
                     "a set difference over in-scope waf_blocks and findings"),
                Part("prescription_prose", DETERMINISTIC, "app.processing.intel.peer", True,
                     "templatable; the comparison is the finding, not the wording"),
            ),
            demoted_because=(
                "The prescription is a set difference between the caller's estate "
                "and the blinded peer aggregate — both already computed. The prose "
                "around it is template-fillable from fields the platform holds, so "
                "it does not clear the residue bar."
            ),
        ),
        Proposition(
            avp="AVP-8",
            title="Risk-delta causal attribution",
            parts=(
                Part("signal_decomposition", DETERMINISTIC,
                     "app.processing.intel.delta", True),
            ),
            residue=(
                "Explain a computed risk movement in terms of external threat "
                "activity: which indicator, which campaign, and why that accounts "
                "for the movement the arithmetic already measured."
            ),
            residue_gate=THREAT_ENRICHMENT,
        ),
        Proposition(
            avp="AVP-9",
            title="Coverage-driven hunt proposals",
            parts=(
                Part("coverage_gap_query_build", DETERMINISTIC, "app.processing.intel.attack", True),
                Part("expected_hit_shape", DETERMINISTIC, "app.processing.intel.attack", True),
                Part("hunt_narrative", DETERMINISTIC, "app.processing.intel.attack", True),
            ),
            demoted_because=(
                "Once AVP-2 produces a coverage gap, the hunt is a query built from "
                "the technique's logsource plus an expected-result count read from "
                "the caller's own data. The narrative is template-fillable."
            ),
        ),
        Proposition(
            avp="AVP-10",
            title="OEM coverage and agreement attestation",
            parts=(
                Part("volume_and_ageing_by_source", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("closure_rate_by_source", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("agreement_attestation", DETERMINISTIC,
                     "app.processing.intel.vendor", True),
                Part("coverage_percentage", DETERMINISTIC, "", False,
                     "uncomputable while no asset inventory exists"),
            ),
            demoted_because=(
                "Counts and ratios over findings and alerts. Built and live. Three of "
                "four parts are shipped; the fourth is blocked on an asset inventory "
                "that does not exist, which is an engineering gap, not an AI gap."
            ),
        ),
        Proposition(
            avp="AVP-11",
            title="Privilege and accountability audit",
            parts=(
                Part("separation_of_duties_conflict", DETERMINISTIC,
                     "app.processing.intel.privilege", True),
                Part("acknowledge_without_authority", DETERMINISTIC,
                     "app.processing.intel.privilege", True),
                Part("scope_violating_export", DETERMINISTIC,
                     "app.processing.intel.privilege", True),
                Part("dormant_account", DETERMINISTIC, "", False,
                     "identity.users.person_id is NULL on all rows"),
            ),
            residue=(
                "Read a behavioural sequence spread across many signed audit rows "
                "and explain it: recognise that a pattern exists which no single "
                "rule would flag."
            ),
            residue_gate=DETECTION_CONTENT,
        ),
        Proposition(
            avp="AVP-12",
            title="Dispute-ready evidence packets",
            parts=(
                Part("packet_assembly", DETERMINISTIC, "app.processing.intel.packet", True),
                Part("hashing_and_signing", DETERMINISTIC, "app.security_pki", True),
                Part("offline_verification", DETERMINISTIC,
                     "app.api.routers.exports_ag", True),
                Part("finding_state_history", DETERMINISTIC, "", False,
                     "findings are upserted in place; no past state is recoverable"),
            ),
            demoted_because=(
                "The platform already signs, hashes and verifies offline for the AG "
                "attestation. A packet is the same primitives applied to a different "
                "selection of rows. No generation anywhere in it."
            ),
        ),
    )
}


def _avp_order(avp: str) -> int:
    """Numeric sort. Plain string sort puts AVP-10 before AVP-2."""
    return int(avp.split("-")[1])


def get(avp: str) -> Proposition:
    try:
        return REGISTRY[avp]
    except KeyError:
        raise KeyError(f"unknown proposition '{avp}'; known: {sorted(REGISTRY)}") from None


def requires_model(avp: str) -> bool:
    """True only where an irreducible deliverable exists."""
    return get(avp).requires_model


def is_deterministic(avp: str) -> bool:
    return not requires_model(avp)


def residues() -> dict[str, str]:
    """The AI-only residue of every proposition that has one."""
    return {a: p.residue for a, p in REGISTRY.items() if p.residue}


def demoted() -> dict[str, str]:
    """Propositions with no AI residue, and the reason each was dropped."""
    return {a: p.demoted_because for a, p in REGISTRY.items() if not p.residue}


def shipped_parts() -> dict[str, tuple[Part, ...]]:
    """Deterministic parts that are built and callable with no model present."""
    out: dict[str, tuple[Part, ...]] = {}
    for avp, prop in REGISTRY.items():
        done = tuple(p for p in prop.deterministic_parts if p.shipped)
        if done:
            out[avp] = done
    return out


def manifest() -> dict:
    """Machine-readable statement of what is deterministic and what is not.

    Returned by ``GET /api/v1/intel/capability`` so the boundary is visible to a
    client rather than only to whoever reads this file.
    """
    key = _avp_order
    props = []
    for avp in sorted(REGISTRY, key=key):
        prop = REGISTRY[avp]
        props.append({
            "avp": avp,
            "title": prop.title,
            "requires_model": prop.requires_model,
            "ai_residue": prop.residue,
            "residue_gate": prop.residue_gate,
            "demoted_because": prop.demoted_because,
            "deterministic_parts": [
                {"name": p.name, "shipped": p.shipped,
                 "implemented_in": p.implemented_in, "blocked_on": p.blocked_on}
                for p in prop.deterministic_parts
            ],
            "gated_parts": [
                {"name": p.name, "reason": p.reason, "blocked_on": p.blocked_on}
                for p in prop.gated_parts
            ],
        })
    return {
        "principle": (
            "Assembly, detection, scoring, correlation, comparison and signing "
            "are deterministic. Only the stated residue needs a model. A "
            "deliverable a template can emit does not count as AI, however much "
            "prose it contains."
        ),
        "reasons": sorted(REASONS),
        "proposition_count": len(REGISTRY),
        "requires_model_count": sum(1 for p in REGISTRY.values() if p.requires_model),
        "demoted_count": sum(1 for p in REGISTRY.values() if not p.residue),
        "with_ai_residue": sorted(residues(), key=key),
        "demoted_to_engineering": sorted(demoted(), key=key),
        "shipped": {a: [p.name for p in parts]
                    for a, parts in sorted(shipped_parts().items(), key=lambda kv: key(kv[0]))},
        "propositions": props,
    }