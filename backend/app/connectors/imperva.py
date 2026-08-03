import aiohttp
import pandas as pd
from app.connectors.base import BaseConnector

class ImpervaConnector(BaseConnector):
    def __init__(self, config: dict):
        source_type = config.get("source_type", "dam")
        super().__init__(f"imperva_{source_type}", config)
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]
        self.source_type = source_type

    async def authenticate(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v1/auth",
                headers={"x-api-key": self.api_key}
            ) as resp:
                return resp.status == 200

    async def poll(self) -> list[dict]:
        results = []
        cursor = None
        async with aiohttp.ClientSession() as session:
            while True:
                params = {"source": self.source_type}
                if cursor:
                    params["cursor"] = cursor
                async with session.get(
                    f"{self.base_url}/api/v1/events",
                    headers={"x-api-key": self.api_key},
                    params=params,
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    items = data.get("events", [])
                    results.extend(items)
                    cursor = data.get("next_cursor")
                    if not cursor:
                        break
        return results

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(raw)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        required = {"event_id", "database_name", "rule_name", "severity"}
        if self.source_type == "waf":
            required = {"event_id", "application_name", "attack_name"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return df
