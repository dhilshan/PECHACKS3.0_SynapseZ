from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import redis
import json
from app.config import settings

# Redis client for rate limiting
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)

def rate_limit(limit: str):
    """Decorator for rate limiting"""
    def decorator(func):
        func._rate_limit = limit
        return func
    return decorator

async def rate_limit_middleware(request: Request, call_next):
    """Custom rate limiting middleware"""
    # Skip rate limiting for certain paths
    if request.url.path in ["/health", "/docs", "/redoc"]:
        return await call_next(request)
    
    # Get rate limit from endpoint
    endpoint = request.app.routes.get(request.url.path)
    if hasattr(endpoint, '_rate_limit'):
        limit = endpoint._rate_limit
    else:
        limit = f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
    
    # Implement rate limiting logic
    key = f"rate_limit:{get_remote_address(request)}:{request.url.path}"
    current = redis_client.get(key)
    
    if current and int(current) >= int(limit.split('/')[0]):
        raise RateLimitExceeded("Rate limit exceeded")
    
    # Increment counter
    redis_client.incr(key)
    redis_client.expire(key, 60)  # Reset after 1 minute
    
    response = await call_next(request)
    return response