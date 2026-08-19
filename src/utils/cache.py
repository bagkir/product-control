import hashlib
import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from src.core.redis_client import get_redis


def make_hash_key(**params: Any) -> str:
    raw = json.dumps(
        params,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.md5(raw.encode()).hexdigest()


def cached(ttl: int, key_prefix: str):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            redis = get_redis()

            key_hash = make_hash_key(
                args=args[1:],
                kwargs=kwargs,
            )

            key = f"{key_prefix}:{key_hash}"

            cached_data = await redis.get(key)

            if cached_data is not None:
                return json.loads(cached_data)

            result = await func(*args, **kwargs)

            await redis.setex(
                key,
                ttl,
                json.dumps(result, default=str),
            )

            return result

        return wrapper

    return decorator


async def invalidate_cache_pattern(pattern: str, client=None) -> None:
    redis_client = client if client is not None else get_redis()

    keys = []
    async for key in redis_client.scan_iter(match=pattern):
        keys.append(key)

    if keys:
        await redis_client.delete(*keys)


async def invalidate_cache_key(key: str, client=None) -> None:
    """Удаляет конкретный ключ. См. invalidate_cache_pattern про client=."""
    redis_client = client if client is not None else get_redis()
    await redis_client.delete(key)
