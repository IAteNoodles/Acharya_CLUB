import time
from typing import Optional

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []

        self._requests[key] = [t for t in self._requests[key] if now - t < window_seconds]

        if len(self._requests[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self._requests[key][0]))
            return False, max(retry_after, 1)

        self._requests[key].append(now)
        return True, 0


async def get_rate_limiter(max_requests: int = 100, window_seconds: int = 60):
    limiter = InMemoryRateLimiter()

    async def rate_limit_dependency(request: Request):
        key = f"rl:{request.client.host}:{request.url.path}"
        allowed, retry_after = limiter.check(key, max_requests, window_seconds)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        return True

    return rate_limit_dependency
