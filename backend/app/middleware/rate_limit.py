import time
import uuid
from typing import Optional

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window rate limiter using in-memory storage (fallback)."""

    def __init__(self):
        self._requests: dict[str, list[float]] = {}

    async def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key] = [t for t in self._requests[key] if now - t < window_seconds]
        if len(self._requests[key]) >= max_requests:
            retry_after = int(window_seconds - (now - self._requests[key][0]))
            return False, max(retry_after, 1)
        self._requests[key].append(now)
        return True, 0


class RedisRateLimiter:
    """Sliding-window rate limiter using Redis sorted sets."""

    def __init__(self, redis):
        self.redis = redis

    async def check(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds

        await self.redis.zremrangebyscore(key, "-inf", window_start)
        count = await self.redis.zcard(key)

        if count >= max_requests:
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(window_seconds - (now - oldest[0][1]))
                return False, max(retry_after, 1)
            return False, 1

        member = f"{now}:{uuid.uuid4()}"
        await self.redis.zadd(key, {member: now})
        await self.redis.expire(key, window_seconds)

        return True, 0


async def get_rate_limiter(
    max_requests: int = 100,
    window_seconds: int = 60,
    redis_client: Optional[object] = None,
    force_in_memory: bool = False,
):
    from app.core.redis import get_redis

    if not force_in_memory and redis_client is None:
        redis_client = await get_redis()

    if redis_client is not None and not force_in_memory:
        limiter = RedisRateLimiter(redis_client)
    else:
        limiter = InMemoryRateLimiter()

    async def rate_limit_dependency(request: Request):
        key = f"rl:{request.client.host}:{request.url.path}"
        allowed, retry_after = await limiter.check(key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        return True

    return rate_limit_dependency
