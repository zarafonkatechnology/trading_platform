# src/mt4_gateway/enhanced_mt4_bridge.py
"""
Enhanced MT4 Bridge - Adds Redis publishing without breaking existing functionality
"""

import os
import json
import logging
import asyncio
from typing import Dict, Optional, List
from datetime import datetime

from src.mt4_gateway.mt4_bridge import MT4Bridge
from src.core.redis_manager import RedisManager

logger = logging.getLogger(__name__)

class EnhancedMT4Bridge(MT4Bridge):
    """
    Enhanced bridge that adds Redis publishing
    Falls back to file-based reading if Redis is not available
    """
    
    def __init__(self):
        super().__init__()
        self.redis = RedisManager()
        self._redis_connected = False
        self._publish_task = None
        
        # Try to connect Redis in background
        asyncio.create_task(self._init_redis())
    
    async def _init_redis(self):
        """Initialize Redis connection in background"""
        try:
            self._redis_connected = await self.redis.connect()
            if self._redis_connected:
                logger.info("✅ Enhanced MT4 Bridge: Redis connected")
                # Start background publisher
                self._publish_task = asyncio.create_task(self._background_publisher())
        except Exception as e:
            logger.warning(f"⚠️ Enhanced MT4 Bridge: Redis init failed: {e}")
    
    async def _background_publisher(self):
        """Background task to publish price updates to Redis"""
        if not self._redis_connected:
            return
        
        last_prices = {}
        
        while True:
            try:
                # Read current prices
                data = self._read_dashboard_file()
                if 'prices' in data:
                    current_prices = data['prices']
                    
                    # Only publish if prices changed
                    if current_prices != last_prices:
                        last_prices = current_prices
                        
                        # Publish to Redis
                        await self.redis.publish(
                            "mt4_prices",
                            json.dumps({
                                'prices': current_prices,
                                'timestamp': datetime.now().isoformat()
                            })
                        )
                        
                        # Cache in Redis
                        await self.redis.set(
                            "current_prices",
                            json.dumps(current_prices),
                            expire=5
                        )
                        
                        logger.debug(f"📊 Published {len(current_prices)} prices to Redis")
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.debug(f"Background publisher error: {e}")
                await asyncio.sleep(5)
    
    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get price - first try Redis, then fallback to file
        """
        # Try Redis first
        if self._redis_connected:
            try:
                # Get from Redis cache
                import asyncio
                cached = asyncio.run(self.redis.get("current_prices"))
                if cached:
                    prices = json.loads(cached)
                    if symbol in prices:
                        return float(prices[symbol])
            except:
                pass
        
        # Fallback to file
        return super().get_price(symbol)
    
    def get_all_prices(self) -> Dict[str, float]:
        """
        Get all prices - first try Redis, then fallback to file
        """
        # Try Redis first
        if self._redis_connected:
            try:
                import asyncio
                cached = asyncio.run(self.redis.get("current_prices"))
                if cached:
                    return json.loads(cached)
            except:
                pass
        
        # Fallback to file
        data = self._read_dashboard_file()
        return data.get('prices', {})