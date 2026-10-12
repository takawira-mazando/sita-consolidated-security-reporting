import logging
from abc import ABC, abstractmethod

import pandas as pd


class BaseConnector(ABC):
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.session = None
        # Provided here so every connector can log without each one having to
        # remember to. AppScanConnector logs on every auth and fetch failure
        # path; without this those paths raised AttributeError and masked the
        # real error (a failed login surfaced as "'AppScanConnector' object has
        # no attribute 'logger'" rather than "authentication failed").
        self.logger = logging.getLogger(f"app.connectors.{name}")

    @abstractmethod
    async def authenticate(self) -> bool:
        pass

    @abstractmethod
    async def poll(self) -> list[dict]:
        pass

    @abstractmethod
    def parse(self, raw: list[dict]) -> pd.DataFrame:
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    async def run(self) -> pd.DataFrame:
        authenticated = await self.authenticate()
        if not authenticated:
            raise ConnectionError(f"{self.name}: authentication failed")
        raw = await self.poll()
        df = self.parse(raw)
        df = self.validate(df)
        return df
