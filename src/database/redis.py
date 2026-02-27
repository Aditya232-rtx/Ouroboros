
import redis
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Lazy pool initialization to avoid crash on import
_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        try:
            _pool = redis.ConnectionPool.from_url(
                settings.redis_url, 
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {e}")
            raise
    return _pool

def get_redis_client():
    """Get a Redis client instance."""
    return redis.Redis(connection_pool=_get_pool())
