import aiohttp
import pandas as pd

from app.connectors.base import BaseConnector


class ApiSecurityConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__("apisec", config)
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]

    async def authenticate(self) -> bool:
        async with aiohttp.ClientSession() as session, session.post(
            f"{self.base_url}/api/v1/auth",
            json={"api_key": self.api_key}
        ) as resp:
            return resp.status == 200

    async def poll(self) -> list[dict]:
        results = []
        offset = 0
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    f"{self.base_url}/api/v1/endpoints",
                    params={"offset": offset, "limit": 100},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    items = data.get("endpoints", [])
                    results.extend(items)
                    if len(items) < 100:
                        break
                    offset += 100
        return results

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(raw)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
