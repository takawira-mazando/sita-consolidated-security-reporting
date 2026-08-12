import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import update

from app.bus.consumer import StreamConsumer
from app.bus.streams import GROUP_DISPATCH, STREAM_ALERTS
from app.config import settings
from app.db import SessionFactory
from app.dispatch.worker import DispatchWorker
from app.lake.writer import record_dispatch
from app.models.alert import Alert

logger = logging.getLogger(__name__)


async def run(consumer_name: str = "dispatch-1"):
    worker = DispatchWorker(max_workers=settings.dispatch_max_workers)
    consumer = StreamConsumer(
        STREAM_ALERTS,
        GROUP_DISPATCH,
        consumer_name,
        handler=lambda mid, f: handle_alert(mid, f, worker),
    )
    stop = asyncio.Event()
    try:
        await consumer.run(stop)
    finally:
        worker.shutdown()
        await consumer.close()


async def handle_alert(msg_id: str, fields: dict, worker: DispatchWorker):
    alert = json.loads(fields["payload"])
    outcomes = await worker.dispatch(alert)
    sent = sum(1 for o in outcomes if o.get("status") == "sent")
    if outcomes:
        logger.info("dispatched alert %s (%s/%s channels)", alert.get("id"), sent, len(outcomes))
    try:
        async with SessionFactory() as session:
            await record_dispatch(session, alert.get("id"), outcomes)
            if outcomes:
                await session.execute(
                    update(Alert)
                    .where(Alert.id == alert.get("id"))
                    .values(last_dispatched_at=datetime.now(timezone.utc))
                )
                await session.commit()
    except Exception:
        logger.exception("failed to persist dispatch audit for alert %s", alert.get("id"))


async def main():
    tasks = [asyncio.create_task(run(f"dispatch-{i+1}")) for i in range(settings.dispatch_consumers)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
