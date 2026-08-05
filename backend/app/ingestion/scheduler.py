import asyncio
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.bus.producer import Producer
from app.bus.streams import STREAM_DLQ, STREAM_RAW
from app.connectors.apisec import ApiSecurityConnector
from app.connectors.appscan import AppScanConnector
from app.connectors.compliance import ComplianceConnector
from app.connectors.imperva import ImpervaConnector
from app.db import SessionFactory
from app.ingestion.circuit_breaker import CircuitBreaker
from app.ingestion.retry import RetryHandler
from app.ingestion.token_bucket import TokenBucket
from app.lake.writer import update_connector_health

scheduler = AsyncIOScheduler()
connectors: dict[str, object] = {}
circuit_breakers: dict[str, CircuitBreaker] = {}
token_buckets: dict[str, TokenBucket] = {}
producer: Producer | None = None

CONNECTOR_CONFIGS = {
    "appscan": {"poll_interval": 300, "rate_limit": 500, "base_url": "", "api_key": ""},
    "imperva_dam": {"poll_interval": 120, "rate_limit": 30, "base_url": "", "api_key": "", "source_type": "dam"},
    "imperva_waf": {"poll_interval": 60, "rate_limit": 600, "base_url": "", "api_key": "", "source_type": "waf"},
    "apisec": {"poll_interval": 3600, "rate_limit": 60, "base_url": "", "api_key": ""},
    "compliance": {"poll_interval": 86400, "rate_limit": 10, "source_type": "csv"},
}

async def poll_connector(name: str, connector_class, config: dict):
    global producer
    cb = circuit_breakers.get(name)
    tb = token_buckets.get(name)
    retry = RetryHandler(max_attempts=3)
    start = time.time()
    try:
        if tb and not await tb.acquire():
            return {"status": "rate_limited", "connector": name}
        connector = connector_class(config)
        result = await cb.call(retry.execute, connector.run)
        count = 0
        if result is not None and not result.empty:
            records = result.to_dict(orient="records")
            if producer is None:
                producer = Producer()
            count = await producer.publish_batch(STREAM_RAW, "raw_record", records, source=name)
        latency = int((time.time() - start) * 1000)
        async with SessionFactory() as session:
            await update_connector_health(session, name, "healthy", latency_ms=latency, records=count)
        return {"status": "success", "connector": name, "records": count}
    except Exception as e:
        if producer is None:
            producer = Producer()
        await producer.publish(STREAM_DLQ, "poll_error", {"connector": name, "error": str(e)}, source=name)
        async with SessionFactory() as session:
            await update_connector_health(session, name, "degraded", error_count=1)
        return {"status": "error", "connector": name, "error": str(e)}

def setup_scheduler():
    for name, config in CONNECTOR_CONFIGS.items():
        cb = CircuitBreaker(name=name, failure_threshold=5, recovery_timeout=120)
        tb = TokenBucket(rate=config["rate_limit"] / 60, capacity=config["rate_limit"], name=name)
        circuit_breakers[name] = cb
        token_buckets[name] = tb
        connector_class = {
            "appscan": AppScanConnector,
            "imperva_dam": ImpervaConnector,
            "imperva_waf": ImpervaConnector,
            "apisec": ApiSecurityConnector,
            "compliance": ComplianceConnector,
        }[name]
        scheduler.add_job(
            poll_connector,
            trigger=IntervalTrigger(seconds=config["poll_interval"]),
            args=[name, connector_class, config],
            id=name,
            name=name,
            max_instances=1,
            misfire_grace_time=30,
        )

def start_scheduler():
    setup_scheduler()
    scheduler.start()

def stop_scheduler():
    scheduler.shutdown(wait=False)

if __name__ == "__main__":
    start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        stop_scheduler()
