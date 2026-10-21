"""AIMI as the provider for the irreducible residue of the gated propositions.

The deterministic layer computes. This package adds the judgement that
``app.processing.intel.capability`` declares no rule can encode: whether a
campaign names this sector, and which indicator accounts for a measured risk
movement.

Two constraints hold the shape of everything in here.

**No module under ``app.processing.intel`` may import this.** ``TestNoModelImports``
in ``backend/tests/test_intel_layer.py`` walks the AST of six deterministic
modules and fails the build on an ``httpx`` import. The residue modules stay
pure: they accept an already-enriched payload and render it. The router is what
crosses the boundary, and it does so in a threadpool.

**Nothing leaves without passing the redaction module.** Outbound payloads are
restricted to public threat identifiers, and a payload carrying an estate,
identity or audit column raises rather than being silently trimmed.
"""
from app.ai.aimi.gateway import (
    ALLOWED_TOOLS,
    EGRESS_DESTINATION_ID,
    REFUSED_TOOLS,
    AimiNotEnabled,
    AimiToolNotAllowed,
    call_tool,
    circuit,
    is_available,
    reset_circuit,
    text_of,
)

__all__ = [
    "ALLOWED_TOOLS",
    "EGRESS_DESTINATION_ID",
    "REFUSED_TOOLS",
    "AimiNotEnabled",
    "AimiToolNotAllowed",
    "call_tool",
    "circuit",
    "is_available",
    "reset_circuit",
    "text_of",
]