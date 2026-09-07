# src/api/middleware/rate_limit.py
"""
Rate limiting middleware
"""

import time
from collections import defaultdict
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """Simple rate limiting middleware"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get client IP
        headers = dict(scope.get("headers", []))
        client_ip = headers.get(b"x-forwarded-for", b"unknown").decode()
        
        # Clean old requests
        current_time = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if current_time - t < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            # In production, return 429 Too Many Requests
            # For now, just log and continue
        
        # Record request
        self.requests[client_ip].append(current_time)
        
        # Process request
        await self.app(scope, receive, send)