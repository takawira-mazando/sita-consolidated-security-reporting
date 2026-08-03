import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.dispatch.email_adapter import EmailAdapter
from app.dispatch.teams_adapter import TeamsAdapter
from app.dispatch.pagerduty_adapter import PagerDutyAdapter


class DispatchWorker:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.email = EmailAdapter()
        self.teams = TeamsAdapter()
        self.pagerduty = PagerDutyAdapter()
        self._threads: ThreadPoolExecutor | None = None

    @property
    def threads(self) -> ThreadPoolExecutor:
        if self._threads is None:
            self._threads = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._threads

    async def dispatch(self, alert: dict) -> int:
        severity = alert.get("severity", "info")
        tasks = []
        if severity in ("critical", "high"):
            tasks.append(asyncio.to_thread(self.email.send, alert))
        tasks.append(self.teams.send(alert))
        if severity == "critical":
            tasks.append(self.pagerduty.send(alert))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(1 for r in results if r is True)

    def shutdown(self):
        if self._threads is not None:
            self._threads.shutdown(wait=True)
