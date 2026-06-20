import os
from typing import Optional
from redis.asyncio import Redis

_redis_instance: Optional[Redis] = None


async def get_redis() -> Optional[Redis]:
    global _redis_instance
    if _redis_instance is not None:
        return _redis_instance

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        _redis_instance = None
        return None

    _redis_instance = Redis.from_url(
        redis_url,
        encoding="utf-8",
        decode_responses=True,
        retry_on_timeout=True,
        socket_keepalive=True,
        socket_connect_timeout=5,
        max_connections=20,
    )
    return _redis_instance


async def close_redis() -> None:
    global _redis_instance
    if _redis_instance is not None:
        await _redis_instance.close()
        _redis_instance = None
