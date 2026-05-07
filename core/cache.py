import redis.asyncio as aioredis
import json
import hashlib
import logging
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)


# Singleton Redis client
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """
    Get or create a Redis client connection.
    
    Reads REDIS_URL from environment. Connection is cached globally.
    
    Returns:
        Connected aioredis.Redis client or None if connection fails
    """
    global _redis_client
    
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.warning("REDIS_URL environment variable not set")
        return None
    
    try:
        _redis_client = aioredis.from_url(redis_url, decode_responses=True)
        # Test connection
        await _redis_client.ping()
        logger.info("Connected to Redis successfully")
        return _redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        _redis_client = None
        return None


def _hash_url(url: str) -> str:
    """
    Generate SHA256 hash of a URL.
    
    Args:
        url: URL to hash
    
    Returns:
        SHA256 hash hex string
    """
    return hashlib.sha256(url.encode()).hexdigest()


def _hash_comparison_urls(url1: str, url2: str) -> str:
    """
    Generate SHA256 hash for a pair of URLs (order-independent).
    
    Sorts the URLs alphabetically, joins them, and hashes.
    This ensures compare(A, B) and compare(B, A) produce the same key.
    
    Args:
        url1: First URL
        url2: Second URL
    
    Returns:
        SHA256 hash hex string
    """
    sorted_urls = sorted([url1, url2])
    combined = "".join(sorted_urls)
    return hashlib.sha256(combined.encode()).hexdigest()


async def get_cached(repo_url: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached repository data from Redis.
    
    Args:
        repo_url: GitHub repository URL
    
    Returns:
        Dictionary with repository data if cached, None otherwise
    """
    try:
        redis = await get_redis()
        if redis is None:
            return None
        
        url_hash = _hash_url(repo_url)
        key = f"reposcope:repo:{url_hash}"
        
        cached_data = await redis.get(key)
        if cached_data is None:
            return None
        
        return json.loads(cached_data)
    
    except Exception as e:
        logger.error(f"Error retrieving cached data for {repo_url}: {e}")
        return None


async def set_cached(
    repo_url: str,
    data: Dict[str, Any],
    ttl_seconds: int = 86400,
) -> bool:
    """
    Cache repository data in Redis with TTL.
    
    Args:
        repo_url: GitHub repository URL
        data: Repository data dictionary to cache
        ttl_seconds: Time-to-live in seconds (default 24 hours)
    
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        redis = await get_redis()
        if redis is None:
            return False
        
        url_hash = _hash_url(repo_url)
        key = f"reposcope:repo:{url_hash}"
        
        json_data = json.dumps(data)
        await redis.setex(key, ttl_seconds, json_data)
        logger.debug(f"Cached data for {repo_url} (TTL: {ttl_seconds}s)")
        return True
    
    except Exception as e:
        logger.error(f"Error caching data for {repo_url}: {e}")
        return False


async def invalidate(repo_url: str) -> bool:
    """
    Remove repository data from cache.
    
    Args:
        repo_url: GitHub repository URL to invalidate
    
    Returns:
        True if invalidated successfully, False otherwise
    """
    try:
        redis = await get_redis()
        if redis is None:
            return False
        
        url_hash = _hash_url(repo_url)
        key = f"reposcope:repo:{url_hash}"
        
        result = await redis.delete(key)
        if result > 0:
            logger.debug(f"Invalidated cache for {repo_url}")
        return result > 0
    
    except Exception as e:
        logger.error(f"Error invalidating cache for {repo_url}: {e}")
        return False


async def get_cached_comparison(url1: str, url2: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached comparison data from Redis.
    
    Order-independent: get_cached_comparison(A, B) and get_cached_comparison(B, A)
    return the same cached data.
    
    Args:
        url1: First repository URL
        url2: Second repository URL
    
    Returns:
        Dictionary with comparison data if cached, None otherwise
    """
    try:
        redis = await get_redis()
        if redis is None:
            return None
        
        url_hash = _hash_comparison_urls(url1, url2)
        key = f"reposcope:compare:{url_hash}"
        
        cached_data = await redis.get(key)
        if cached_data is None:
            return None
        
        return json.loads(cached_data)
    
    except Exception as e:
        logger.error(f"Error retrieving cached comparison data: {e}")
        return None


async def set_cached_comparison(
    url1: str,
    url2: str,
    data: Dict[str, Any],
    ttl_seconds: int = 86400,
) -> bool:
    """
    Cache comparison data in Redis with TTL.
    
    Order-independent: set_cached_comparison(A, B, data) and 
    set_cached_comparison(B, A, data) store to the same cache key.
    
    Args:
        url1: First repository URL
        url2: Second repository URL
        data: Comparison data dictionary to cache
        ttl_seconds: Time-to-live in seconds (default 24 hours)
    
    Returns:
        True if cached successfully, False otherwise
    """
    try:
        redis = await get_redis()
        if redis is None:
            return False
        
        url_hash = _hash_comparison_urls(url1, url2)
        key = f"reposcope:compare:{url_hash}"
        
        json_data = json.dumps(data)
        await redis.setex(key, ttl_seconds, json_data)
        logger.debug(f"Cached comparison data (TTL: {ttl_seconds}s)")
        return True
    
    except Exception as e:
        logger.error(f"Error caching comparison data: {e}")
        return False
