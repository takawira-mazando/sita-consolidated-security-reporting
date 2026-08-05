"""Load OEM-shaped fixtures for tests and the seed-simulated pipeline."""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent

SOURCE_FILES = {
    "appscan": "appscan_findings.json",
    "imperva_dam": "imperva_dam_events.json",
    "imperva_waf": "imperva_waf_events.json",
    "apisec": "apisec_endpoints.json",
    "compliance": "compliance_rows.json",
}


def load_fixture(source: str) -> list[dict]:
    if source not in SOURCE_FILES:
        raise ValueError(f"unknown fixture source: {source}")
    path = FIXTURES_DIR / SOURCE_FILES[source]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_fixtures() -> dict[str, list[dict]]:
    return {source: load_fixture(source) for source in SOURCE_FILES}
