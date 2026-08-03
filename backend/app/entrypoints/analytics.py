import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.bus.producer import Producer, make_redis
from app.bus.streams import STREAM_ALERTS
from app.config import settings
from app.db import SessionFactory
from app.lake.writer import upsert_alerts, upsert_risk_scores
from app.processing.alert_engine import AlertRuleEngine
from app.processing.risk_aggregator import compute_all_risk_scores

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def run_aggregate_rules() -> list[dict]:
    redis = make_redis()
    engine = AlertRuleEngine(redis=redis)
    producer = Producer()
    try:
        async with SessionFactory() as session:
            alerts = await engine.evaluate_aggregate(session)
        if alerts:
            async with SessionFactory() as session:
                await upsert_alerts(session, alerts)
            await producer.publish_batch(STREAM_ALERTS, "alert", alerts)
        logger.info("aggregate rules produced %d alerts", len(alerts))
        return alerts
    finally:
        await producer.close()
        await redis.aclose()


async def run_risk_computation() -> int:
    async with SessionFactory() as session:
        rows = await compute_all_risk_scores(session)
        await upsert_risk_scores(session, rows)
    logger.info("computed risk scores for %d apps", len(rows))
    return len(rows)


def setup_scheduler():
    scheduler.add_job(
        run_aggregate_rules,
        trigger=IntervalTrigger(seconds=settings.analytics_aggregate_rules_interval),
        id="aggregate_rules",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    scheduler.add_job(
        run_risk_computation,
        trigger=IntervalTrigger(seconds=settings.analytics_risk_interval),
        id="risk_computation",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )


async def main():
    setup_scheduler()
    scheduler.start()
    logger.info("analytics scheduler started")
    try:
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
