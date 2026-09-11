import aiohttp
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

from app.connectors.base import BaseConnector


class AppScanConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__("appscan", config)
        self.base_url = config.get("base_url", "https://cloud.appscan.com").rstrip("/")
        self.api_key = config.get("api_key", "")
        self.account_id = config.get("account_id", "")
        self.application_id = config.get("application_id", "")
        self.page_size = config.get("page_size", 200)
        self.scope = config.get("scope", "application")
        self.token = None
        self.token_expiry = None

    async def authenticate(self) -> bool:
        if not self.api_key:
            self.logger.error("AppScan API key not configured")
            return False

        # Parse api_key as "key_id:key_secret" or use separate config fields
        key_id = self.config.get("key_id") or self.api_key.split(":")[0] if ":" in self.api_key else self.api_key
        key_secret = self.config.get("key_secret") or self.api_key.split(":")[1] if ":" in self.api_key else ""

        if not key_secret:
            self.logger.error("AppScan key_secret not configured (provide as 'key_id:key_secret' in api_key or separate key_secret field)")
            return False

        url = f"{self.base_url}/api/v4/Account/ApiKeyLogin"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"KeyId": key_id, "KeySecret": key_secret}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.token = data.get("token") or data.get("access_token")
                        expires_in = data.get("expires_in", 1500)
                        self.token_expiry = datetime.now(timezone.utc).timestamp() + expires_in - 300
                        self.logger.info("AppScan authentication successful")
                        return True
                    else:
                        text = await resp.text()
                        self.logger.error(f"AppScan auth failed: {resp.status} - {text}")
                        return False
        except Exception as e:
            self.logger.error(f"AppScan auth exception: {e}")
            return False

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

            items = data.get("items", []) or data.get("Issues", []) or data.get("issues", []) or []
            has_more = len(items) >= limit
            if "has_more" in data:
                has_more = data["has_more"]
            elif "total" in data and "offset" in data:
                has_more = (data["offset"] + len(items)) < data["total"]

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
        if not dt_str:
            return None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]:
            try:
                dt = datetime.strptime(dt_str, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue
        return None

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        if not raw:
            return pd.DataFrame()

        records = []
        for item in raw:
            issue_id = item.get("id") or item.get("IssueId") or item.get("issue_id")
            app_name = item.get("application_name") or item.get("ApplicationName") or item.get("app_name")
            vuln_name = item.get("vulnerability_name") or item.get("VulnerabilityName") or item.get("name")
            description = item.get("description") or item.get("Description") or ""
            severity_raw = item.get("severity") or item.get("Severity") or item.get("risk_level")
            status = item.get("status") or item.get("Status") or "Open"
            first_found = item.get("first_found_date") or item.get("FirstFoundDate") or item.get("created_at")
            last_found = item.get("last_found_date") or item.get("LastFoundDate") or item.get("updated_at")
            cve = item.get("cve") or item.get("Cve") or item.get("cve_id")
            cvss = item.get("cvss") or item.get("CvssScore") or item.get("cvss_score")
            owasp = item.get("owasp_category") or item.get("OwaspCategory") or item.get("cwe")

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
                "cvss_score": float(cvss) if cvss else None,
                "owasp_category": owasp,
                "raw_data": item,
            }
            records.append(record)

        return pd.DataFrame(records)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
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