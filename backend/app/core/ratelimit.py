"""Small fixed-window rate limiter. Uses Redis when reachable, otherwise in-process memory."""
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.core.config import settings

_mem: dict[str, tuple[int, float]] = defaultdict(lambda: (0, 0.0))
_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        try:
            import redis

            _redis = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)
            _redis.ping()
        except Exception:
            _redis = False
    return _redis or None


def hit(key: str, limit: int, window: int) -> bool:
    """Return True if the call is allowed."""
    r = _get_redis() if settings.env != "test" else None
    if r:
        try:
            k = f"rl:{key}:{int(time.time() // window)}"
            n = r.incr(k)
            if n == 1:
                r.expire(k, window)
            return n <= limit
        except Exception:
            pass
    count, start = _mem[key]
    now = time.time()
    if now - start > window:
        count, start = 0, now
    count += 1
    _mem[key] = (count, start)
    return count <= limit


def limiter(name: str, limit: int, window: int):
    def dep(request: Request):
        if not settings.rate_limit_enabled:
            return
        ip = request.client.host if request.client else "unknown"
        if not hit(f"{name}:{ip}", limit, window):
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    return dep


def reset():
    _mem.clear()
