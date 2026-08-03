import os
import pandas as pd
import yaml
from datetime import datetime
from typing import Any
import hashlib

SEVERITY_MAP = {
    "appscan": {"4 - Critical": "critical", "3 - High": "high", "2 - Medium": "medium", "1 - Low": "low", "Informational": "info"},
    "imperva": {"Emergency": "critical", "Alert": "critical", "Critical": "critical", "Error": "high", "Warning": "medium", "Notice": "low", "Info": "info"},
    "apisec": {},
}

NORMALISED = {"info", "low", "medium", "high", "critical"}

DEFAULT_FIELD_MAPPER_PATH = os.path.join(os.path.dirname(__file__), "field_mapper.yaml")

class Normaliser:
    def __init__(self, field_mapper_path: str = DEFAULT_FIELD_MAPPER_PATH):
        self.field_maps = self._load_field_maps(field_mapper_path)

    def _load_field_maps(self, path: str) -> dict:
        try:
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}

    def normalise(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        df = self._flatten_fields(df, source)
        df = self._normalise_severity(df, source)
        df = self._normalise_timestamps(df)
        df = self._cast_types(df)
        df = self._dedup(df, source)
        return df

    def _flatten_fields(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        return df

    def _normalise_severity(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        severity_map = SEVERITY_MAP.get(source, {})
        if "severity" in df.columns:
            if severity_map:
                df["severity"] = df["severity"].map(
                    lambda v: v if isinstance(v, str) and v.strip().lower() in NORMALISED else severity_map.get(v)
                ).fillna("info")
            else:
                df["severity"] = df["severity"].map(
                    lambda v: v.strip().lower() if isinstance(v, str) else "info"
                )
        return df

    def _normalise_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        for col in ["first_seen", "last_seen", "timestamp", "discovered_at"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        return df

    def _cast_types(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def _dedup(self, df: pd.DataFrame, source: str) -> pd.DataFrame:
        key_cols = [c for c in ["id", "event_id", "external_id"] if c in df.columns]
        if key_cols:
            df = df.drop_duplicates(subset=key_cols)
        return df
