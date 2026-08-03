import asyncio
import json
import logging
from collections import defaultdict

import pandas as pd
from redis.exceptions import ResponseError

from app.bus.producer import Producer, make_redis
from app.bus.streams import STREAM_ALERTS, STREAM_RAW, STREAM_DLQ, GROUP_PROCESSING
from app.config import settings
from app.db import SessionFactory
from app.lake.writer import upsert_lake_batch
from app.processing.normaliser import Normaliser
from app.processing.alert_engine import AlertRuleEngine

logger = logging.getLogger(__name__)


def _normalise_records(records: list[dict], source: str, normaliser: Normaliser) -> list[dict]:
    """CPU-bound pandas work, meant to run in a thread."""
    if not records:
        return []
    df = normaliser.normalise(pd.DataFrame(records), source)
    if df.empty:
        return []
    rows = df.to_dict(orient="records")
    for row in rows:
        row["source"] = source
    return rows


async def process_batch(
    entries: list[tuple[str, dict]],
    normaliser: Normaliser,
    engine: AlertRuleEngine,
    producer: Producer,
) -> None:
    if not entries:
        return

    by_source: dict[str, list[dict]] = defaultdict(list)
    failed: list[tuple[str, dict]] = []
    for msg_id, fields in entries:
        try:
            payload = json.loads(fields["payload"])
            record = payload if isinstance(payload, dict) else {"records": payload}
            by_source[fields.get("source", "unknown")].append(record)
        except Exception as exc:
            logger.exception("failed to parse message %s: %s", msg_id, exc)
            failed.append((msg_id, fields))
            await producer.publish(
                STREAM_DLQ,
                "parse_error",
                {"original_id": msg_id, "error": str(exc), "fields": fields},
            )

    normalized = await asyncio.gather(
        *(
            asyncio.to_thread(_normalise_records, records, source, normaliser)
            for source, records in by_source.items()
        )
    )
    rows: list[dict] = []
    for batch_rows, (source, _) in zip(normalized, by_source.items()):
        for row in batch_rows:
            rows.append(row)

    if rows:
        alerts: list[dict] = []
        sem = asyncio.Semaphore(settings.processing_max_concurrent_evals)

        async def evaluate(row: dict):
            async with sem:
                return await engine.evaluate(row)

        results = await asyncio.gather(*(evaluate(row) for row in rows))
        for row, found in zip(rows, results):
            for alert in found:
                alert.setdefault("severity", "info")
                alert["source"] = alert.get("source") or row.get("source", "")
                alerts.append(alert)

        try:
            async with SessionFactory() as session:
                await upsert_lake_batch(session, rows, alerts=alerts)
        except Exception as exc:
            logger.exception("lake write failed: %s", exc)
            for msg_id, _ in entries:
                await producer.publish(
                    STREAM_DLQ,
                    "lake_write_error",
                    {"original_id": msg_id, "error": str(exc)},
                )

        if alerts:
            await producer.publish_batch(STREAM_ALERTS, "alert", alerts)


async def run(
    consumer_name: str = "processing-1",
    batch_size: int | None = None,
    block_ms: int = 2000,
):
    batch_size = batch_size or settings.processing_batch_size
    normaliser = Normaliser()
    redis = make_redis()
    engine = AlertRuleEngine(redis=redis)
    producer = Producer()
    try:
        await redis.xgroup_create(STREAM_RAW, GROUP_PROCESSING, id="0", mkstream=True)
    except ResponseError:
        pass
    try:
        while True:
            messages = await redis.xreadgroup(
                GROUP_PROCESSING,
                consumer_name,
                {STREAM_RAW: ">"},
                count=batch_size,
                block=block_ms,
            )
            if not messages:
                continue
            entries = [
                (msg_id, fields)
                for _stream, batch in messages
                for msg_id, fields in batch
            ]
            await process_batch(entries, normaliser, engine, producer)
            if entries:
                await redis.xack(
                    STREAM_RAW,
                    GROUP_PROCESSING,
                    *[msg_id for msg_id, _ in entries],
                )
    finally:
        await producer.close()
        await redis.aclose()


async def main():
    consumers = settings.processing_consumers
    tasks = [asyncio.create_task(run(f"processing-{i+1}")) for i in range(consumers)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
