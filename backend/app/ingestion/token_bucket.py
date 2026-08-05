import asyncio
import time


class TokenBucket:
    def __init__(self, rate: float, capacity: int | None = None, name: str = "default"):
        self.rate = rate
        self.capacity = capacity or int(rate)
        self.tokens = self.capacity
        self.last_refill = time.monotonic()
        self.name = name

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    async def acquire(self, tokens: int = 1) -> bool:
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    async def acquire_blocking(self, tokens: int = 1, timeout: float = 30.0):
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            if await self.acquire(tokens):
                return True
            await asyncio.sleep(0.1)
        raise TimeoutError(f"TokenBucket {self.name}: timeout waiting for {tokens} tokens")
