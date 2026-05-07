import json
import redis.asyncio as aioredis

# Answers are cached for 24 hours. Long enough to deduplicate repeated queries
# within a session; short enough that a rebuilt vector DB won't serve stale
# answers indefinitely.
_CACHE_TTL_SECONDS = 86_400

_redis = aioredis.Redis(host="localhost", port=6379, db=0)


async def get_cache(key: str) -> str | None:
    data = await _redis.get(key)
    return json.loads(data) if data else None


async def store_cache(key: str, value: str) -> None:
    await _redis.set(key, json.dumps(value), ex=_CACHE_TTL_SECONDS)
