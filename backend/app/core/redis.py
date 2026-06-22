import os
from typing import Optional, Union

from redis.asyncio import Redis as RedisPy

# Upstash REST-based Redis (no persistent TCP connection needed)
try:
    from upstash_redis.asyncio import Redis as UpstashRedis  # type: ignore[import-untyped]
except ImportError:
    UpstashRedis = None  # type: ignore[assignment]

AnyRedis = Union[RedisPy, "UpstashRedis"]

_redis_instance: Optional[AnyRedis] = None
_upstash_url: str = ""
_upstash_token: str = ""


def _is_upstash() -> bool:
    return bool(_upstash_url and _upstash_token and UpstashRedis is not None)


async def get_redis() -> Optional[AnyRedis]:
    global _redis_instance, _upstash_url, _upstash_token

    if _redis_instance is not None:
        return _redis_instance

    _upstash_url = os.getenv("UPSTASH_REDIS_REST_URL", "")
    _upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

    if _is_upstash():
        _redis_instance = UpstashRedis(
            url=_upstash_url,
            token=_upstash_token,
        )
        return _redis_instance

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        _redis_instance = None
        return None

    _redis_instance = RedisPy.from_url(
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
