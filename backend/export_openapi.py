"""Extract the OpenAPI/Swagger spec from the local dev application.

Why this exists
---------------
The checked-in ``openapi.json`` is stale. It documents 45 paths and predates the
entire ``/api/v1/intel`` and ``/api/v1/reports-ai`` surface, including every
AI route. An API contract that silently omits half the product is worse than no
contract, because it looks authoritative. This regenerates it from the live
application so the two cannot diverge again.

The spec is DEV-ONLY. ``app/main.py`` instantiates FastAPI with
``docs_url=None, redoc_url=None, openapi_url=None`` outside dev/test (finding
R-05), so this endpoint does not exist in staging or production. Anything
extracted here describes an interface a deployed instance will not serve, and
must not be published as a client-facing contract without that caveat.

No credentials are written: the schema is built from route and model metadata,
and ``Settings`` is not an exposed dependency. A scan for key-shaped strings
runs below as a guard rather than as an assumption.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from app.main import app

OUT_DIR = Path(__file__).resolve().parent.parent
TARGET = OUT_DIR / "openapi.json"

#: Patterns that would indicate a credential reached the spec.
SECRET_PATTERNS = (
    re.compile(r"aimi_[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)\b(?:password|secret|api[_-]?key)\s*[=:]\s*[\"'][^\"']{8,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\."),
)


def main() -> int:
    schema = app.openapi()

    leaked = [
        pattern.pattern for pattern in SECRET_PATTERNS
        if pattern.search(json.dumps(schema))
    ]
    if leaked:
        print("ABORT: credential-shaped strings found in the schema:")
        for item in leaked:
            print(f"  {item}")
        return 1

    paths = schema["paths"]

    # Capture the previous contract BEFORE writing. Reading it afterwards would
    # compare the new file against itself and report a diff of zero.
    #
    # utf-8-sig, because the checked-in file carries a BOM: json.loads raises on
    # a plain utf-8 read, and a swallowed parse error would report "was 0 paths"
    # as though the previous contract were empty. A parse failure is reported,
    # never smoothed over into a zero.
    previous_paths: set[str] = set()
    comparison_note = ""
    if TARGET.exists():
        try:
            previous_paths = set(
                json.loads(
                    TARGET.read_text(encoding="utf-8-sig")
                ).get("paths", {})
            )
        except (ValueError, OSError) as exc:
            comparison_note = (
                f"  previous file unreadable ({exc.__class__.__name__}); "
                f"no comparison made"
            )
    else:
        comparison_note = "  no previous file to compare against"

    json_path = TARGET
    json_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    try:
        import yaml
        yaml_path = OUT_DIR / "openapi.yaml"
        yaml_path.write_text(
            yaml.safe_dump(schema, sort_keys=False, width=100, allow_unicode=True),
            encoding="utf-8",
        )
        yaml_written = f"  {yaml_path.name:<16} {yaml_path.stat().st_size:>9,} bytes"
    except ImportError:
        yaml_written = "  openapi.yaml       skipped (PyYAML not installed)"

    paths = schema["paths"]
    print(f"SITA Security Intelligence Platform — OpenAPI {schema['openapi']}")
    print(f"  title           {schema['info']['title']} v{schema['info']['version']}")
    print(f"  paths           {len(paths)}")
    print(f"  operations      {sum(len(m) for m in paths.values())}")
    print()
    print("Written:")
    print(f"  openapi.json{'':<9} {json_path.stat().st_size:>9,} bytes")
    print(yaml_written)
    print()
    print("DEV-ONLY: /openapi.json is disabled outside dev/test (R-05, app/main.py:60-75).")

    new_paths = set(paths)
    added = sorted(new_paths - previous_paths)
    removed = sorted(previous_paths - new_paths)
    print()
    print("Compared with the previous tracked openapi.json:")
    if comparison_note:
        print(comparison_note)
    else:
        print(f"  was              {len(previous_paths)} paths")
    print(f"  now              {len(new_paths)} paths")
    print(f"  added            {len(added)}")
    print(f"  removed          {len(removed)}")

    if removed:
        print()
        print("  REMOVED (a contract that loses endpoints is a regression):")
        for path in removed:
            print(f"    {path}")

    ai = [p for p in sorted(new_paths) if "/intel" in p or "reports-ai" in p]
    if ai:
        print()
        print(f"  AI/intelligence surface now documented ({len(ai)} paths):")
        for path in ai:
            methods = ",".join(sorted(m.upper() for m in paths[path]))
            print(f"    {methods:<10} {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())