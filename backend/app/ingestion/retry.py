import asyncio
import random
from collections.abc import Callable
from typing import Any


class RetryHandler:
    def __init__(self, max_attempts: int = 3, backoff_base: float = 2.0,
                 backoff_max: float = 60.0, jitter: bool = True):
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.jitter = jitter

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exception = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts:
                    delay = min(self.backoff_base ** attempt, self.backoff_max)
                    if self.jitter:
                        delay *= 1 + random.random()  # nosec B311
                    await asyncio.sleep(delay)
        raise last_exception
