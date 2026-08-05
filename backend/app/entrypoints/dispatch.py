import asyncio
import json
import logging

from app.bus.consumer import StreamConsumer
from app.bus.streams import GROUP_DISPATCH, STREAM_ALERTS
from app.config import settings
from app.dispatch.worker import DispatchWorker

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
    sent = await worker.dispatch(alert)
    if sent:
        logger.info("dispatched alert %s (%s channels)", alert.get("id"), sent)


async def main():
    tasks = [asyncio.create_task(run(f"dispatch-{i+1}")) for i in range(settings.dispatch_consumers)]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
