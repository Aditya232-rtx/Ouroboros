
import redis
from config.settings import settings

# Create a connection pool
pool = redis.ConnectionPool.from_url(
    settings.redis_url, 
    decode_responses=True
)

def get_redis_client():
    """Get a Redis client instance."""
    return redis.Redis(connection_pool=pool)
