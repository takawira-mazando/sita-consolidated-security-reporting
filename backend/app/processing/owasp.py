"""OWASP Top 10 classification for normalised findings.

Why this exists
---------------
AppScan already ships an OWASP tag, so it lands in ``findings.category`` as
``A03-injection``. Nothing else does. Imperva DAM writes ``sql_injection``,
Imperva WAF writes ``sqli``, API Security writes ``shadow_api``, and the
compliance connector writes POPIA domain names into the same column. One
``GROUP BY category`` across the estate therefore grouped six incompatible
vocabularies together, which is why the AppSec dashboard could not honestly be
called an OWASP view.

This module maps every source's vocabulary onto OWASP Top 10 2021 so that a
rollup means the same thing whatever produced the row.

Three properties this deliberately does *not* have
-------------------------------------------------
1. **It never guesses.** An unmapped value yields ``UNMAPPED`` with a reason,
   not a nearest-neighbour guess. A wrong OWASP id in an assurance artefact is
   worse than an admitted gap, and the gap is measurable.
2. **It never overwrites the OEM.** ``category`` is left exactly as the vendor
   sent it. This classification is additive; the OEM's own taxonomy remains
   available for anyone who needs it.
3. **It never claims compliance sources.** A POPIA consent gap is an assurance
   obligation, not a software weakness. Forcing it into A01-A10 would repeat
   the category error this module exists to remove.

The mapping data is versioned in ``owasp_mapping.yaml`` so a reviewer can read
what every vendor value maps to and diff it when OWASP publishes a new edition.
The same shape as ``alert_rules.yaml`` and ``field_mapper.yaml``: configuration,
not code.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

MAPPING_PATH = os.path.join(os.path.dirname(__file__), "owasp_mapping.yaml")

#: Outcome vocabulary. Every classification lands in exactly one of these.
CLASSIFIED = "classified"
UNMAPPED = "unmapped"
NOT_APPLICABLE = "not_applicable"
ABSENT = "absent"

#: Sources exempt from OWASP classification, resolved from the mapping file so
#: the exemption is reviewable alongside the rules it constrains.

_CWE_RE = re.compile(r"cwe[-_/ ]*(\d+)", re.IGNORECASE)
_OWASP_ID_RE = re.compile(r"^a(0[1-9]|10)\b", re.IGNORECASE)


@dataclass(frozen=True)
class OwaspCategory:
    id: str
    name: str
    summary: str


@dataclass(frozen=True)
class Classification:
    """One finding's OWASP position. ``None`` id means *not classified*, and
    ``status`` says which of the three non-classified states applies."""

    owasp_id: str | None
    owasp_name: str | None
    cwe_id: str | None
    taxonomy_version: str
    status: str
    reason: str | None = None
    mapped_from: str | None = None

    @property
    def classified(self) -> bool:
        return self.owasp_id is not None


@lru_cache(maxsize=1)
def _config() -> dict:
    try:
        with open(MAPPING_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


@lru_cache(maxsize=1)
def categories() -> dict[str, OwaspCategory]:
    raw = _config().get("categories") or {}
    return {
        str(cid).upper(): OwaspCategory(
            id=str(cid).upper(),
            name=str(body.get("name") or cid),
            summary=str(body.get("summary") or "").strip(),
        )
        for cid, body in raw.items()
    }


def taxonomy_version() -> str:
    return str(_config().get("version") or "owasp-top10-2021")


@lru_cache(maxsize=1)
def _rules() -> dict[str, dict[str, str]]:
    raw = _config().get("rules") or {}
    out: dict[str, dict[str, str]] = {}
    for source, mapping in raw.items():
        out[str(source).lower()] = {
            str(k).strip().lower(): str(v).upper() for k, v in (mapping or {}).items()
        }
    return out


@lru_cache(maxsize=1)
def _cwe_rules() -> dict[str, str]:
    raw = _config().get("cwe") or {}
    return {str(k).strip(): str(v).upper() for k, v in raw.items()}


@lru_cache(maxsize=1)
def _exempt_sources() -> frozenset[str]:
    return frozenset(
        str(s).strip().lower() for s in (_config().get("exempt_sources") or [])
    )


def exempt_sources() -> set[str]:
    """Sources whose vocabulary is not a software vulnerability class."""
    return set(_exempt_sources())


def _rules_for(source: str) -> dict[str, str]:
    """Resolve a source to its mapping, mirroring Normaliser._source_map."""
    rules = _rules()
    if not rules:
        return {}
    key = (source or "").strip().lower()
    if key in rules:
        return rules[key]
    for candidate, mapping in rules.items():
        if candidate in key or key.startswith(candidate):
            return mapping
    # AppScan ships as `appscan` and `appscan_real` in different connectors.
    if key.startswith("appscan"):
        return rules.get("appscan", {})
    return {}


def _canonical_from_id(value: str) -> str | None:
    """Accept `A01:2021`, `A01-broken-access-control`, `A01`."""
    match = _OWASP_ID_RE.match(value.strip())
    if not match:
        return None
    candidate = f"A{match.group(1)}"
    return candidate if candidate in categories() else None


def extract_cwe(value: str) -> str | None:
    match = _CWE_RE.search(value)
    return f"CWE-{match.group(1)}" if match else None


def classify(category: object, source: str) -> Classification:
    """Classify one raw category value for one source.

    Order matters and is deliberate:
      1. Exempt source  -> not_applicable (never a guess)
      2. Absent value   -> absent
      3. Already an OWASP id -> pass through
      4. CWE identifier -> derive from the CWE table, keep the CWE
      5. Source mapping -> vendor vocabulary
      6. Otherwise      -> unmapped, with the value echoed so it can be curated
    """
    version = taxonomy_version()
    src = (source or "").strip().lower()

    if src in _exempt_sources():
        return Classification(
            owasp_id=None,
            owasp_name=None,
            cwe_id=None,
            taxonomy_version=version,
            status=NOT_APPLICABLE,
            reason="source vocabulary is not a software vulnerability class",
        )

    raw = "" if category is None else str(category).strip()
    if not raw or raw.lower() in {"nan", "nat", "none"}:
        return Classification(
            owasp_id=None,
            owasp_name=None,
            cwe_id=None,
            taxonomy_version=version,
            status=ABSENT,
            reason="no category supplied by the source",
        )

    # 3. already an OWASP id, in any of the shapes seen in the wild
    direct = _canonical_from_id(raw)
    if direct:
        return Classification(
            owasp_id=direct,
            owasp_name=categories()[direct].name,
            cwe_id=extract_cwe(raw),
            taxonomy_version=version,
            status=CLASSIFIED,
            mapped_from=raw,
        )

    # 4. CWE is precise, so it is preserved and mapped through the CWE table
    cwe = extract_cwe(raw)
    if cwe:
        target = _cwe_rules().get(cwe.split("-", 1)[1])
        if target and target in categories():
            return Classification(
                owasp_id=target,
                owasp_name=categories()[target].name,
                cwe_id=cwe,
                taxonomy_version=version,
                status=CLASSIFIED,
                mapped_from=raw,
            )

    # 5. vendor vocabulary
    target = _rules_for(src).get(raw.lower())
    if target and target in categories():
        return Classification(
            owasp_id=target,
            owasp_name=categories()[target].name,
            cwe_id=cwe,
            taxonomy_version=version,
            status=CLASSIFIED,
            mapped_from=raw,
        )

    # 6. an explicit maintenance backlog, not a silent wrong answer
    return Classification(
        owasp_id=None,
        owasp_name=None,
        cwe_id=cwe,
        taxonomy_version=version,
        status=UNMAPPED,
        reason=f"no OWASP mapping defined for {raw!r} from source {src!r}",
    )


def classify_all(records: list[dict], source: str) -> list[Classification]:
    return [classify(r.get("category"), source) for r in records]


def as_dicts() -> list[dict]:
    """Registry shape for the API and the dashboard."""
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "summary": cat.summary,
            "taxonomy_version": taxonomy_version(),
        }
        for cat in sorted(categories().values(), key=lambda c: c.id)
    ]


def known_statuses() -> set[str]:
    return {CLASSIFIED, UNMAPPED, NOT_APPLICABLE, ABSENT}
