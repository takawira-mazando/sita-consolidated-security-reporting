import asyncio

from app.ingestion.scheduler import start_scheduler, stop_scheduler


async def main():
    start_scheduler()
    try:
        await asyncio.Event().wait()
    finally:
        stop_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
