import json
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _make_key(domain_id: str, query: str) -> str:
    return f"reguchat:{domain_id}:{query}"


async def get_cache(domain_id: str, key: str) -> Optional[str]:
    data = await get_redis().get(_make_key(domain_id, key))
    return json.loads(data) if data else None


async def store_cache(domain_id: str, key: str, value: str) -> None:
    await get_redis().set(
        _make_key(domain_id, key),
        json.dumps(value),
        ex=settings.cache_ttl_seconds,
    )
