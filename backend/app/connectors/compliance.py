import aiohttp
import pandas as pd
from app.connectors.base import BaseConnector

class ComplianceConnector(BaseConnector):
    def __init__(self, config: dict):
        super().__init__("compliance", config)
        self.source_type = config.get("source_type", "csv")
        self.file_path = config.get("file_path")
        self.api_url = config.get("api_base_url")

    async def authenticate(self) -> bool:
        if self.source_type == "csv":
            return True
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/health"
            ) as resp:
                return resp.status == 200

    async def poll(self) -> list[dict]:
        if self.source_type == "csv" and self.file_path:
            import csv
            results = []
            with open(self.file_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
            return results
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_url}/api/v1/controls"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("controls", [])
                return []

    def parse(self, raw: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(raw)

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        return df
