import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.dispatch.email_adapter import EmailAdapter
from app.dispatch.pagerduty_adapter import PagerDutyAdapter
from app.dispatch.teams_adapter import TeamsAdapter

logger = logging.getLogger(__name__)

# Fallback routing when an alert carries no explicit channels (e.g. legacy/seed alerts).
DEFAULT_CHANNELS = {
    "critical": ["email", "teams", "pagerduty"],
    "high": ["email", "teams"],
    "medium": ["teams"],
    "low": ["teams"],
    "info": ["teams"],
}


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

    def channels_for(self, alert: dict) -> list[str]:
        channels = alert.get("channels")
        if isinstance(channels, list) and channels:
            return channels
        return DEFAULT_CHANNELS.get(str(alert.get("severity", "info")).lower(), ["teams"])

    async def dispatch(self, alert: dict) -> list[dict]:
        """Dispatch an alert across its channels, returning per-channel outcomes.

        Returns a list of dicts: {channel, status: sent|failed|skipped, error}.
        Routing honours the rule-declared ``channels`` (falling back to a
        severity-based default), so the executed policy matches the YAML.
        """
        channels = self.channels_for(alert)
        severity = str(alert.get("severity", "info")).lower()
        now = datetime.now(timezone.utc)
        tasks = []
        for channel in channels:
            if channel == "email" and severity in ("critical", "high"):
                tasks.append((channel, asyncio.to_thread(self.email.send, alert)))
            elif channel == "teams":
                tasks.append((channel, self.teams.send(alert)))
            elif channel == "pagerduty" and severity == "critical":
                tasks.append((channel, self.pagerduty.send(alert)))
        if not tasks:
            logger.warning("alert %s has no dispatchable channels (%s)", alert.get("id"), channels)
            return []

        results = await asyncio.gather(*(t for _, t in tasks), return_exceptions=True)
        outcomes: list[dict] = []
        for (channel, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                outcomes.append({
                    "channel": channel,
                    "status": "failed",
                    "error": str(result),
                    "attempted_at": now.isoformat(),
                })
                logger.error("dispatch %s failed for alert %s: %s", channel, alert.get("id"), result)
            elif result is True:
                outcomes.append({
                    "channel": channel,
                    "status": "sent",
                    "error": None,
                    "attempted_at": now.isoformat(),
                })
            else:
                outcomes.append({
                    "channel": channel,
                    "status": "failed",
                    "error": "adapter returned False",
                    "attempted_at": now.isoformat(),
                })
        return outcomes

    def shutdown(self):
        if self._threads is not None:
            self._threads.shutdown(wait=True)
