import json
import uuid
from datetime import datetime, timezone

from redis import asyncio as aioredis

from app.config import settings


def make_redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def build_message(event_type: str, payload: dict, source: str = "") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "source": source,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload": json.dumps(payload, default=str),
    }


class Producer:
    def __init__(self, redis: aioredis.Redis | None = None, maxlen: int = 100_000):
        self.redis = redis or make_redis()
        self.maxlen = maxlen

    async def publish(
        self,
        stream: str,
        event_type: str,
        payload: dict,
        source: str = "",
    ) -> str:
        return await self.redis.xadd(
            stream,
            build_message(event_type, payload, source),
            maxlen=self.maxlen,
            approximate=True,
        )

    async def publish_batch(
        self,
        stream: str,
        event_type: str,
        records: list[dict],
        source: str = "",
    ) -> int:
        if not records:
            return 0
        pipe = self.redis.pipeline(transaction=False)
        for record in records:
            pipe.xadd(
                stream,
                build_message(event_type, record, source),
                maxlen=self.maxlen,
                approximate=True,
            )
        await pipe.execute()
        return len(records)

    async def close(self):
        await self.redis.aclose()
