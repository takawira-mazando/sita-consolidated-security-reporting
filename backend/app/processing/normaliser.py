import os
from collections.abc import Callable

import pandas as pd
import yaml

SEVERITY_MAP = {
    "appscan": {"4 - Critical": "critical", "3 - High": "high", "2 - Medium": "medium", "1 - Low": "low", "Informational": "info"},
    "imperva": {"Emergency": "critical", "Alert": "critical", "Critical": "critical", "Error": "high", "Warning": "medium", "Notice": "low", "Info": "info"},
    "apisec": {},
}

NORMALISED = {"info", "low", "medium", "high", "critical"}

DEFAULT_FIELD_MAPPER_PATH = os.path.join(os.path.dirname(__file__), "field_mapper.yaml")

# Canonical warehouse column ordering used by lake/writer.py record_to_finding()
CANONICAL_COLUMNS = [
    "external_id", "app_name", "title", "description", "category",
    "first_seen", "last_seen", "status", "severity",
]

TYPE_HINTS = {
    "appscan": {"cvss": "float", "cve": "str"},
    "imperva": {"rows_affected": "int"},
    "apisec": {"exposure_score": "float", "is_shadow": "bool"},
}


def _extract_path(record: dict, path: str):
    """Resolve a `$.a.b[0].c` style path against a nested dict/list."""
    if not path:
        return None
    current = record
    for token in path.lstrip("$.").replace(".[", ".").replace("[", ".").replace("]", "").split("."):
        if token == "":  # nosec B105
            continue
        if isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError, TypeError):
                return None
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            return None
    return current


class Normaliser:
    def __init__(self, field_mapper_path: str = DEFAULT_FIELD_MAPPER_PATH):
        self.field_maps = self._load_field_maps(field_mapper_path)

    def _load_field_maps(self, path: str) -> dict:
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def _source_map(self, source: str) -> dict:
        maps = self.field_maps.get("sources", {})
        # map 'imperva_dam'/'imperva_waf' to the 'imperva' severity map fallback
        if source in maps:
            return maps[source]
        for key, value in maps.items():
            if key in source or source.startswith(key):
                return value
        return {}

    # ---------------------------------------------------------------- fields
    def _flatten_fields(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        """Config-driven flatten: field_mapper.yaml maps OEM paths -> canonical columns."""
        mapping = self._source_map(source).get("field_mappings", {})
        if not mapping or df.empty:
            return df

        out: dict[str, list] = {canonical: [] for canonical in mapping}
        out.setdefault("severity", [])
        for record in df.to_dict(orient="records"):
            for canonical, path in mapping.items():
                out.setdefault(canonical, []).append(_extract_path(record, path))
            out["severity"].append(record.get("severity"))
        flattened = pd.DataFrame(out)
        # preserve any already-canonical columns not covered by the mapping
        for col in df.columns:
            if col in {"severity"} or col in mapping.values():
                continue
            flattened[col] = df[col].values
        return flattened

    # -------------------------------------------------------------- severity
    def _normalise_severity(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        if "severity" not in df.columns:
            df["severity"] = "info"
        source_map = self._source_map(source)
        severity_map = source_map.get("severity_map") or SEVERITY_MAP.get(source, {})

        # API Security: derive severity from exposure score (config-driven thresholds)
        if source == "apisec" or isinstance(severity_map, dict) and severity_map.get("exposure_based"):
            thresholds = severity_map.get("thresholds") or {}
            df["severity"] = df.apply(
                lambda r: self._apisec_severity(r, thresholds), axis=1
            )
            return df

        def map_one(value):
            if isinstance(value, (int, float)):
                value = str(int(value))
            value = str(value or "").strip()
            if value.lower() in NORMALISED:
                return value.lower()
            if severity_map:
                mapped = severity_map.get(value)
                if mapped:
                    return mapped
            # numeric fallback 4->critical ... 1->low
            num = {"4": "critical", "3": "high", "2": "medium", "1": "low"}
            if value in num:
                return num[value]
            return "info"

        df["severity"] = df["severity"].map(map_one)
        return df

    @staticmethod
    def _apisec_severity(record: dict, thresholds: dict | None = None) -> str:
        thresholds = thresholds or {}
        exposure = record.get("exposure_score")
        try:
            exposure = float(exposure)
        except (TypeError, ValueError):
            return "info"
        critical_at = float(thresholds.get("critical", 80))
        high_at = float(thresholds.get("high", 50))
        medium_at = float(thresholds.get("medium", 20))
        if exposure >= critical_at:
            return "critical"
        if exposure >= high_at:
            return "high"
        if exposure >= medium_at:
            return "medium"
        return "low"

    # ----------------------------------------------------------- timestamps
    def _normalise_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["first_seen", "last_seen", "timestamp", "discovered_at", "block_time"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        # derive first/last_seen from whatever timestamp columns survived flatten
        if "first_seen" not in df.columns and "timestamp" in df.columns:
            df["first_seen"] = df["timestamp"]
        if "last_seen" not in df.columns and "timestamp" in df.columns:
            df["last_seen"] = df["timestamp"]
        return df

    # ---------------------------------------------------------------- types
    def _cast_types(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        hints = TYPE_HINTS.get(source, {})
        for col, dtype in hints.items():
            if col not in df.columns:
                continue
            try:
                if dtype == "float":
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                elif dtype == "int":
                    df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                elif dtype == "bool":
                    df[col] = df[col].map(
                        lambda v: str(v).strip().lower() in ("true", "1", "yes")
                        if not isinstance(v, bool) else v
                    )
            except (ValueError, TypeError):
                continue
        return df

    # ----------------------------------------------------------------- dedup
    def _dedup(self, df: pd.DataFrame, source: str, lookup: Callable | None = None) -> pd.DataFrame:
        """In-batch dedup by external id, plus optional 1h window DB lookup.

        `lookup(records)` -> dict[external_id, dict] of existing records seen in
        the last hour. When a record exists with the same status we keep the
        newest and let the writer's ON CONFLICT touch last_seen (version++).
        """
        key_cols = [c for c in ["external_id", "event_id", "id", "api_id", "control_id"] if c in df.columns]
        if key_cols:
            df = df.drop_duplicates(subset=key_cols, keep="last")
        if lookup is not None and "external_id" in df.columns:
            pending = df.to_dict(orient="records")
            seen = lookup(pending) or {}
            keep: list[dict] = []
            for record in pending:
                ext = record.get("external_id")
                if ext in seen:
                    existing = seen[ext]
                    if existing.get("status") == record.get("status"):
                        # same status within window -> suppress insert, update last_seen only
                        continue
                keep.append(record)
            df = pd.DataFrame(keep, columns=df.columns) if keep else df.iloc[0:0]
        return df

    # ---------------------------------------------------------------- public
    def normalise(self, df: pd.DataFrame, source: str, lookup: Callable | None = None) -> pd.DataFrame:
        df = self._flatten_fields(df, source)
        df = self._normalise_severity(df, source)
        df = self._normalise_timestamps(df)
        df = self._cast_types(df, source)
        df = self._dedup(df, source, lookup=lookup)
        if df.empty:
            return df
        # enforce canonical ordering / default app_name
        for col in list(CANONICAL_COLUMNS):
            if col not in df.columns:
                df[col] = None
        if "app_name" in df.columns:
            df["app_name"] = df["app_name"].fillna("unknown")
        return df[CANONICAL_COLUMNS]
