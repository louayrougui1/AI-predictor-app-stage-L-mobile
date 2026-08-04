import logging

from fastapi import HTTPException, Request

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

IP_LIMIT = 10
KEY_LIMIT = 5
WINDOW = 60


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First entry is the original client; the rest are intermediate proxies
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _increment(key: str, window: int) -> int:
    pipe = redis_client.pipeline()
    pipe.incr(key)
    pipe.expire(key, window, nx=True)  # only set TTL on first increment
    attempts, _ = await pipe.execute()
    return attempts


async def check_rate_limit(
    request: Request,
    key: str,
    *,
    scope: str | None = None,
    ip_limit: int = IP_LIMIT,
    key_limit: int = KEY_LIMIT,
    window: int = WINDOW,
):
    scope = scope or request.url.path.strip("/").replace("/", ":")
    client_ip = get_client_ip(request)

    ip_key = f"rate:{scope}:ip:{client_ip}"
    id_key = f"rate:{scope}:key:{key}"

    ip_attempts = await _increment(ip_key, window)
    logger.info("rate-limit scope=%s ip=%s attempts=%s", scope, client_ip, ip_attempts)

    if ip_attempts > ip_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests from this IP Retry-After: {str(window)} seconds",
            headers={"Retry-After": str(window)},
        )

    id_attempts = await _increment(id_key, window)
    logger.info("rate-limit scope=%s key=%s attempts=%s", scope, key, id_attempts)

    if id_attempts > key_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests for this account: {str(window)} seconds",
            headers={"Retry-After": str(window)},
        )