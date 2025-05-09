from typing import Any, Optional, Union
import json
import redis
from datetime import timedelta
import logging
from src.config.settings import REDIS_URL, REDIS_TTL

logger = logging.getLogger("uqifeed")

class Cache:
    """Redis-based caching utility"""
    
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL)
        self.default_ttl = REDIS_TTL
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds or timedelta
            
        Returns:
            bool: True if successful
        """
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            ttl = ttl or self.default_ttl
            
            return self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if successful
        """
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            bool: True if successful
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                return bool(self.redis.delete(*keys))
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return False

# Initialize cache instance
cache = Cache()

# Cache decorator
def cached(
    ttl: Optional[Union[int, timedelta]] = None,
    key_prefix: str = "",
    key_builder: Optional[callable] = None
):
    """
    Cache decorator for functions
    
    Args:
        ttl: Time to live in seconds or timedelta
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                key_parts = [key_prefix, func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Get fresh value
            value = await func(*args, **kwargs)
            
            # Cache the value
            await cache.set(cache_key, value, ttl)
            
            return value
        return wrapper
    return decorator 