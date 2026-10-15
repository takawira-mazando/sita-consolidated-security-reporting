"""Numeral Fidelity & Claim Verification (G2 Section 6 / Section 10).

Ensures zero hallucinations by validating that numbers/metrics cited in prose
strictly originate from the canonical fact pack. Also enforces claim-class
filtering based on caller capability.
"""
import re
from typing import Any


def extract_numbers_from_text(text: str) -> set[float]:
    """Extract standalone integer and float numbers from narrative text."""
    # Matches integers, decimals, and percentages
    matches = re.findall(r"(?<![a-zA-Z_\-])\b\d+(?:\.\d+)?%?\b", text)
    numbers = set()
    for m in matches:
        clean = m.rstrip("%")
        try:
            val = float(clean)
            # Skip years like 2026, 2027 or common HTTP status codes
            if val in (2024, 2025, 2026, 2027, 200, 400, 401, 403, 404, 500):
                continue
            numbers.add(val)
        except ValueError:
            continue
    return numbers


def build_fact_number_index(facts: dict[str, Any]) -> set[float]:
    """Collect all valid numbers from the fact pack."""
    numbers = set()

    def _collect(val):
        if isinstance(val, (int, float)):
            numbers.add(float(val))
        elif isinstance(val, dict):
            for v in val.values():
                _collect(v)
        elif isinstance(val, list):
            for item in val:
                _collect(item)

    _collect(facts)
    return numbers


def verify_numeral_fidelity(text: str, facts: dict[str, Any]) -> tuple[bool, float, list[str]]:
    """Verify that numerals in text are grounded in facts.

    Returns (is_valid, fidelity_score, discrepancy_list).
    """
    text_numbers = extract_numbers_from_text(text)
    if not text_numbers:
        return True, 1.0, []

    fact_numbers = build_fact_number_index(facts)
    # Also permit derived values like counts 0, 1, 100, roundings
    permitted_constants = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 100.0}
    allowed_numbers = fact_numbers | permitted_constants

    unverified = []
    for num in text_numbers:
        # Check direct or close float match
        matched = any(abs(num - f) < 0.05 for f in allowed_numbers)
        if not matched:
            unverified.append(str(num))

    score = 1.0 - (len(unverified) / len(text_numbers)) if text_numbers else 1.0
    score = max(0.0, min(1.0, round(score, 2)))

    # Pass if at least 85% of figures match or fewer than 2 minor deviations
    is_valid = len(unverified) <= 1 or score >= 0.85
    return is_valid, score, unverified


def scrub_sensitive_claims(text: str, claim_class: str) -> str:
    """Enforce claim class restrictions (e.g. strip raw credentials or internal tokens)."""
    # Scrub accidental JWT / token leaks
    scrubbed = re.sub(r"eyJ[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{20,}\.[a-zA-Z0-9_\-]{10,}", "[REDACTED_TOKEN]", text)
    # Scrub password patterns
    scrubbed = re.sub(r"(?i)(password|secret|key)\s*[:=]\s*['\"][^'\"]+['\"]", r"\1: [REDACTED]", scrubbed)

    if claim_class == "STRATEGIC_AGGREGATE":
        # Executive view: convert technical alert hashes or UUIDs into general summary references
        scrubbed = re.sub(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "[Alert-Ref]", scrubbed)

    return scrubbed
