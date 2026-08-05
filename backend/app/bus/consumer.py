import asyncio
import json
import logging
from collections.abc import Callable

from redis import asyncio as aioredis
from redis.exceptions import ResponseError

from app.bus.streams import STREAM_DLQ

logger = logging.getLogger(__name__)


class StreamConsumer:
    def __init__(
        self,
        stream: str,
        group: str,
        consumer: str,
        handler: Callable[[dict, dict], None] | None = None,
        redis: aioredis.Redis | None = None,
        batch_size: int = 10,
        block_ms: int = 5000,
    ):
        self.stream = stream
        self.group = group
        self.consumer = consumer
        self.handler = handler
        self.redis = redis
        self.batch_size = batch_size
        self.block_ms = block_ms
        self._own_redis = redis is None
        if self.redis is None:
            from app.bus.producer import make_redis
            self.redis = make_redis()

    async def ensure_group(self):
        try:
            await self.redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except ResponseError:
            pass

    async def process_once(self, max_messages: int | None = None):
        messages = await self.redis.xreadgroup(
            self.group,
            self.consumer,
            {self.stream: ">"},
            count=self.batch_size,
            block=self.block_ms,
        )
        if not messages:
            return 0
        handled = 0
        for _stream, entries in messages:
            for msg_id, fields in entries:
                try:
                    if self.handler:
                        await self.handler(msg_id, fields)
                    await self.redis.xack(self.stream, self.group, msg_id)
                    handled += 1
                except Exception as exc:
                    logger.exception("message %s failed: %s", msg_id, exc)
                    await self.nack(msg_id, fields)
                if max_messages is not None and handled >= max_messages:
                    return handled
        return handled

    async def nack(self, msg_id: str, fields: dict):
        try:
            await self.redis.xadd(
                STREAM_DLQ,
                {
                    "original_stream": self.stream,
                    "original_id": msg_id,
                    "consumer": self.consumer,
                    "reason": "handler_error",
                    "payload": json.dumps(fields),
                },
                maxlen=10_000,
                approximate=True,
            )
        except Exception:
            logger.exception("failed to write DLQ entry for %s", msg_id)

    async def run(self, stop_event: asyncio.Event | None = None):
        await self.ensure_group()
        while stop_event is None or not stop_event.is_set():
            try:
                await self.process_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("consumer loop error on %s", self.stream)
                await asyncio.sleep(2)

    async def close(self):
        if self._own_redis:
            await self.redis.aclose()
