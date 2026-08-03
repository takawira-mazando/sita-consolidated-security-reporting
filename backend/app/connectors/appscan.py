import aiohttp
import pandas as pd
from app.connectors.base import BaseConnector

class AppScanConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__("appscan", config)
        self.base_url = config["base_url"]
        self.api_key = config["api_key"]
        self.page_size = config.get("page_size", 200)
        self.token = None

    async def authenticate(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/v4/authenticate",
                headers={"x-api-key": self.api_key}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get("token")
                    return True
                return False

    async def poll(self) -> list[dict]:
        if not self.token:
            raise RuntimeError("Not authenticated")
        results = []
        offset = 0
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(
                    f"{self.base_url}/api/v4/findings",
                    headers={"Authorization": f"Bearer {self.token}"},
                    params={"offset": offset, "limit": self.page_size}
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    items = data.get("items", [])
                    results.extend(items)
                    if len(items) < self.page_size:
                        break
                    offset += self.page_size
        return results

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(raw)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        required = {"id", "application_name", "vulnerability_name", "severity"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        return df
