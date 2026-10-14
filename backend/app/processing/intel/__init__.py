"""Deterministic intelligence layer.

Holds the parts of the value-proposition set that need no model, so that a
model is spent only where generation or external enrichment is genuinely
required. See :mod:`app.processing.intel.capability` for the boundary and the
reasoning behind it.

Every module here is a join, an aggregate, or arithmetic over columns the
warehouse already carries. None of them opens a network connection, reads a
file, or calls a model. That property is the point: each is testable with every
AI dependency switched off, reproducible run to run, and safe to sign.

New AI work should arrive here first and move out to a gated module only if a
reviewer can name the thing that is impossible to compute.
"""
from app.processing.intel import (
    attack,
    author_rules,
    behaviour,
    campaign,
    capability,
    causal,
    controls,
    delta,
    estate,
    packet,
    peer,
    popia,
    privilege,
    vendor,
)
from app.processing.intel.capability import (
    DETECTION_CONTENT,
    DETERMINISTIC,
    LEGAL_GUIDANCE,
    THREAT_ENRICHMENT,
    Proposition,
    demoted,
    get,
    is_deterministic,
    manifest,
    requires_model,
    residues,
    shipped_parts,
)
from app.processing.intel.controls import CATALOGUE, assess, iso_status
from app.processing.intel.delta import app_delta, decompose, largest_movers
from app.processing.intel.estate import estate_graph
from app.processing.intel.packet import build as build_packet
from app.processing.intel.peer import prescribe
from app.processing.intel.privilege import privilege_audit
from app.processing.intel.vendor import attestation, contradictions

__all__ = [
    # modules
    "attack",
    "author_rules",
    "behaviour",
    "campaign",
    "capability",
    "causal",
    "controls",
    "delta",
    "estate",
    "packet",
    "peer",
    "popia",
    "privilege",
    "vendor",
    # symbols
    "CATALOGUE",
    "DETERMINISTIC",
    "DETECTION_CONTENT",
    "LEGAL_GUIDANCE",
    "THREAT_ENRICHMENT",
    "Proposition",
    "app_delta",
    "assess",
    "attestation",
    "build_packet",
    "contradictions",
    "decompose",
    "demoted",
    "estate_graph",
    "get",
    "is_deterministic",
    "iso_status",
    "prescribe",
    "residues",
    "largest_movers",
    "manifest",
    "privilege_audit",
    "requires_model",
    "shipped_parts",
]