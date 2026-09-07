# src/core/redis_manager.py
"""
Redis Manager - OPTIONAL caching layer
Falls back gracefully if Redis is not available
"""

import json
import logging
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis manager with graceful fallback - won't break anything if Redis is down"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self, url: str = "redis://localhost:6379/0"):
        """Connect to Redis - fails gracefully if Redis not available"""
        try:
            import aioredis
            self._client = await aioredis.from_url(url, decode_responses=True)
            await self._client.ping()
            logger.info("✅ Redis connected")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e} - Using fallback mode")
            self._client = None
            return False
    
    async def get(self, key: str) -> Optional[str]:
        """Get from cache - returns None if Redis not available"""
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except:
            return None
    
    async def set(self, key: str, value: str, expire: int = 60):
        """Set in cache - fails gracefully"""
        if not self._client:
            return
        try:
            await self._client.setex(key, expire, value)
        except:
            pass
    
    async def publish(self, channel: str, message: str):
        """Publish to channel - fails gracefully"""
        if not self._client:
            return
        try:
            await self._client.publish(channel, message)
        except:
            pass
    
    async def subscribe(self, channel: str):
        """Subscribe to channel - returns None if Redis not available"""
        if not self._client:
            return None
        try:
            pubsub = self._client.pubsub()
            await pubsub.subscribe(channel)
            return pubsub
        except:
            return None
    
    async def get_or_set(self, key: str, callback, expire: int = 60):
        """Get from cache or execute callback and cache result"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        result = await callback()
        if result:
            await self.set(key, json.dumps(result), expire)
            return result
        return None