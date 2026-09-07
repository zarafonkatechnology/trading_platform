# src/api/middleware/logging.py
"""
Request logging middleware
"""

import logging
import time
from fastapi import Request
from typing import Callable

logger = logging.getLogger(__name__)

class LoggingMiddleware:
    """Log all requests and responses"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Log request
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Process request
        await self.app(scope, receive, send)
        
        # Log response time
        duration = time.time() - start_time
        logger.info(f"Response: {request.method} {request.url.path} - {duration:.3f}s")