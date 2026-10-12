import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp
import pandas as pd

from app.connectors.base import BaseConnector


def _ci(source: dict, *names: str, default=None):
    """Case-insensitive, first-match field lookup.

    AppScan Cloud v4 returns PascalCase (``Id``, ``IssueType``, ``LastFound``).
    The connector was originally written against lowercase fixture payloads, so
    a literal ``item.get("id")`` silently produced ``None`` against the real API
    and every finding was dropped by validation. Matching case-insensitively
    keeps both shapes working and stops a casing change on AppScan's side from
    becoming a silent data-loss event.
    """
    if not isinstance(source, dict):
        return default
    for name in names:
        if name in source:
            value = source[name]
            if value not in (None, ""):
                return value
    lowered = {str(k).lower(): v for k, v in source.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value not in (None, ""):
            return value
    return default


class AppScanConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__("appscan", config)
        self.base_url = config.get("base_url", "https://cloud.appscan.com").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.account_id = config.get("account_id", "")
        self.application_id = config.get("application_id", "")
        # Human-readable name for this application, used as app_name when the
        # API response carries no ApplicationName field (which is the common
        # case for the AppScan Cloud v4 Issues endpoint). Falls back to the
        # application_id UUID if not configured, and the UUID is also in
        # tenant.APP_DEPARTMENTS as a safety net for rows already in the DB.
        self.application_name = config.get(
            "application_name",
            config.get("app_name", self.application_id),
        )
        self.page_size = config.get("page_size", 200)
        self.scope = config.get("scope", "application")
        self.token = None
        self.token_expiry = None


    def _credentials(self) -> tuple[str, str]:
        """Resolve the API key pair from config.

        Two supported shapes:

        - separate ``key_id`` and ``key_secret`` fields (what AppScan issues,
          and what settings.appscan_key_id / appscan_key_secret hold), or
        - a single combined ``api_key`` in ``key_id:key_secret`` form.

        Split on the *first* colon only, because a secret may itself contain one.
        """
        key_id = (self.config.get("key_id") or "").strip()
        key_secret = (self.config.get("key_secret") or "").strip()
        if key_id and key_secret:
            return key_id, key_secret

        combined = (self.api_key or "").strip()
        if ":" in combined:
            first, _, remainder = combined.partition(":")
            return first.strip(), remainder.strip()
        if combined and not key_id:
            return combined, ""
        return key_id, key_secret

    async def authenticate(self) -> bool:
        key_id, key_secret = self._credentials()
        if not key_id or not key_secret:
            # Both halves are required: AppScan issues a key pair, and a key id
            # alone cannot authenticate. This used to guard on `self.api_key`,
            # which is the *combined* form -- so supplying the documented
            # separate key_id/key_secret fields bailed out here as "not
            # configured" before the pair was ever used.
            self.logger.error(
                "AppScan credentials not configured: provide key_id and "
                "key_secret (or a combined 'key_id:key_secret' in api_key)"
            )
            return False

        url = f"{self.base_url}/api/v4/Account/ApiKeyLogin"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json={"KeyId": key_id, "KeySecret": key_secret}
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        self.logger.error(
                            "AppScan auth failed: %s - %s", resp.status, text[:300]
                        )
                        return False
                    data = await resp.json()
        except Exception as e:
            self.logger.error("AppScan auth exception: %s", e)
            return False

        # AppScan Cloud returns PascalCase: {"Token": ..., "Expire": <ISO8601>}.
        # Match case-insensitively so a casing change on their side surfaces as
        # a clear "no token in response" rather than a silent None.
        lowered = {str(k).lower(): v for k, v in (data or {}).items()}
        token = lowered.get("token") or lowered.get("access_token")
        if not token:
            self.logger.error(
                "AppScan auth returned HTTP 200 but no token field; keys=%s",
                sorted((data or {}).keys()),
            )
            return False

        self.token = token
        self.token_expiry = self._parse_expiry(lowered)
        self.logger.info("AppScan authentication successful")
        return True

    def _parse_expiry(self, lowered: dict) -> float:
        """Resolve token expiry as an absolute epoch timestamp.

        AppScan sends an absolute ``Expire`` timestamp. A relative ``expires_in``
        is accepted as a fallback. If neither is usable the token is treated as
        already expired so the next call re-authenticates rather than sending a
        stale credential and getting an opaque 401.
        """
        expire = lowered.get("expire") or lowered.get("expires_at")
        if expire:
            parsed = self._parse_datetime(str(expire))
            if parsed is not None:
                return parsed.timestamp()

        seconds = lowered.get("expires_in")
        if seconds:
            try:
                return datetime.now(timezone.utc).timestamp() + float(seconds) - 300
            except (TypeError, ValueError):
                pass
        return datetime.now(timezone.utc).timestamp()

    def _token_valid(self) -> bool:
        if not self.token or not self.token_expiry:
            return False
        return datetime.now(timezone.utc).timestamp() < self.token_expiry

    async def _ensure_authenticated(self):
        if not self._token_valid():
            await self.authenticate()

    async def _fetch_issues_page(
        self, session: aiohttp.ClientSession, offset: int, limit: int
    ) -> tuple[list[dict], bool]:
        scope_id = self.application_id or self.account_id
        if not scope_id:
            self.logger.error("No application_id or account_id configured for scope")
            return [], True

        url = f"{self.base_url}/api/v4/Issues/{self.scope}/{scope_id}"
        params = {"offset": offset, "limit": limit}

        try:
            async with session.get(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                params=params
            ) as resp:
                if resp.status == 401:
                    self.token = None
                    self.token_expiry = None
                    await self.authenticate()
                    async with session.get(
                        url,
                        headers={"Authorization": f"Bearer {self.token}"},
                        params=params
                    ) as retry_resp:
                        if retry_resp.status != 200:
                            text = await retry_resp.text()
                            self.logger.error(f"AppScan issues fetch failed after re-auth: {retry_resp.status} - {text}")
                            return [], True
                        data = await retry_resp.json()
                elif resp.status != 200:
                    text = await resp.text()
                    self.logger.error(f"AppScan issues fetch failed: {resp.status} - {text}")
                    return [], True
                else:
                    data = await resp.json()

            items = _ci(data, "items") or _ci(data, "issues") or []
            has_more = len(items) >= limit
            total = _ci(data, "total")
            offset = _ci(data, "offset")
            has_more_flag = _ci(data, "has_more")
            if has_more_flag is not None:
                has_more = bool(has_more_flag)
            elif total is not None and offset is not None:
                has_more = (int(offset) + len(items)) < int(total)

            return items, has_more

        except Exception as e:
            self.logger.error(f"AppScan fetch exception: {e}")
            return [], True

    async def poll(self) -> list[dict]:
        await self._ensure_authenticated()
        if not self.token:
            raise RuntimeError("AppScan authentication failed")

        results = []
        offset = 0

        async with aiohttp.ClientSession() as session:
            while True:
                items, has_more = await self._fetch_issues_page(session, offset, self.page_size)
                results.extend(items)
                if not has_more:
                    break
                offset += self.page_size

        self.logger.info(f"AppScan fetched {len(results)} issues")
        return results

    def _normalize_severity(self, severity: str) -> int:
        severity_map = {
            "1 - low": 1, "low": 1, "informational": 1, "info": 1,
            "2 - medium": 2, "medium": 2,
            "3 - high": 3, "high": 3,
            "4 - critical": 4, "critical": 4,
        }
        return severity_map.get(str(severity).lower().strip(), 1)

    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """Parse an AppScan/.NET ISO-8601 timestamp.

        AppScan emits 7-digit fractional seconds
        (``2026-08-24T09:28:00.2831764Z``) because it is a .NET service. Python's
        ``%f`` accepts at most 6 digits, so every such value failed to parse and
        came back None -- and ``validate`` then dropped the row, silently
        discarding 79 of 83 real findings.

        The fraction is truncated to microsecond precision rather than rounded, so
        a timestamp never rolls into the next second.
        """
        if not dt_str:
            return None
        candidate = str(dt_str).strip()

        match = re.match(r"^(.*?\.)(\d+)(Z|[+-]\d{2}:?\d{2})$", candidate)
        if match:
            head, frac, suffix = match.groups()
            candidate = f"{head}{frac[:6]}{'Z' if suffix == 'Z' else suffix}"

        for fmt in [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                dt = datetime.strptime(candidate, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        try:
            dt = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        if not raw:
            return pd.DataFrame()

        records = []
        for item in raw:
            issue_id = _ci(item, "id", "IssueId", "issue_id")
            # The Issues API returns ApplicationId but no application name.
            # Falling back to the configured application id keeps the row
            # identifiable rather than failing validation, since app_name is
            # what drives tenant mapping downstream.
            app_name = (
                _ci(item, "application_name", "ApplicationName", "app_name")
                or self.application_name
            )
            # IssueType carries the human-readable vulnerability name.
            vuln_name = _ci(
                item,
                "vulnerability_name",
                "VulnerabilityName",
                "IssueType",
                "name",
                "rule_name",
            )
            description = _ci(item, "description", "Description", "Context", default="")
            severity_raw = _ci(item, "severity", "Severity", "risk_level")
            status = _ci(item, "status", "Status", default="Open")
            first_found = _ci(
                item, "first_found_date", "FirstFoundDate", "DateCreated", "created_at"
            )
            last_found = _ci(
                item,
                "last_found_date",
                "LastFoundDate",
                "LastFound",
                "LastUpdated",
                "updated_at",
            )
            cve = _ci(item, "cve", "Cve", "cve_id", "CveId")
            cvss = _ci(item, "cvss", "CvssScore", "cvss_score", "Cvss")
            # AppScan exposes CWE as a bare numeric id (`"Cwe": 311`). That is a
            # CWE identifier, not an OWASP category, so it feeds `cwe` and never
            # the OWASP category fallback -- otherwise a bare int would travel
            # through field_mapper's `category <- owasp_category` mapping and be
            # written into a VARCHAR column as "311".
            cwe_id = _ci(item, "Cwe", "cwe_id")
            if cwe_id is not None:
                cwe_text = str(cwe_id).strip()
                if cwe_text.isdigit():
                    cve = cve or f"CWE-{cwe_text}"
            owasp = _ci(item, "owasp_category", "OwaspCategory")

            record = {
                "external_id": str(issue_id) if issue_id else None,
                "source": "appscan",
                "application_name": app_name,
                "vulnerability_name": vuln_name,
                "description": description,
                "severity": self._normalize_severity(severity_raw),
                "severity_raw": str(severity_raw) if severity_raw else None,
                "status": status,
                "first_found_date": self._parse_datetime(first_found),
                "last_found_date": self._parse_datetime(last_found),
                "cve": cve,
                "cvss_score": float(cvss) if cvss is not None else None,
                "owasp_category": owasp,
                "raw_data": item,
            }
            records.append(record)

        return pd.DataFrame(records)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        # An application with no findings is a valid, normal poll result. It
        # must return an empty frame rather than raising, otherwise every empty
        # poll is routed to the DLQ as a connector defect and looks like an
        # outage when it is simply "nothing to report".
        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "external_id", "source", "application_name",
                    "vulnerability_name", "description", "severity",
                    "severity_raw", "status", "first_found_date",
                    "last_found_date", "cve", "cvss_score", "owasp_category",
                    "raw_data",
                ]
            )

        required = {"external_id", "application_name", "vulnerability_name", "severity"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        initial_len = len(df)
        df = df.dropna(subset=["external_id", "application_name", "vulnerability_name", "severity"])
        if len(df) < initial_len:
            self.logger.warning(f"Dropped {initial_len - len(df)} rows with missing required fields")

        if "first_found_date" in df.columns:
            df = df.dropna(subset=["first_found_date"])

        return df