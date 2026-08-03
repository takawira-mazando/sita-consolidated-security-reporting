import hashlib
import time
from collections import defaultdict


class AlertDeduplicator:
    """Throttle suppression shared across consumers via Redis, with in-memory fallback."""

    def __init__(self, redis=None):
        self.redis = redis
        self.throttle_cache: dict[str, list[float]] = defaultdict(list)

    def _make_key(self, rule_id: str, source_id: str, target_id: str, severity: str) -> str:
        raw = f"{rule_id}:{source_id}:{target_id}:{severity}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def is_suppressed(
        self,
        rule_id: str,
        source_id: str,
        target_id: str,
        severity: str,
        window_minutes: int = 60,
        max_alerts: int = 1,
    ) -> bool:
        key = self._make_key(rule_id, source_id, target_id, severity)
        now = time.time()
        window_seconds = window_minutes * 60
        if self.redis is not None:
            rkey = f"sita:throttle:{key}"
            await self.redis.zremrangebyscore(rkey, 0, now - window_seconds)
            count = await self.redis.zcard(rkey)
            if count >= max_alerts:
                return True
            await self.redis.zadd(rkey, {str(now): now})
            await self.redis.expire(rkey, window_seconds + 60)
            return False
        self.throttle_cache[key] = [
            t for t in self.throttle_cache[key]
            if now - t < window_seconds
        ]
        if len(self.throttle_cache[key]) >= max_alerts:
            return True
        self.throttle_cache[key].append(now)
        return False
