# src/api/simple_main.py
"""
Simplified FastAPI application for testing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Platform API (Test)",
    version="1.0.0-test"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "Trading Platform API (Test)",
        "status": "online",
        "message": "API is working!"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/ping")
async def ping():
    return {"pong": "API is responsive"}

if __name__ == "__main__":
    logger.info("Starting test API server...")
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000,
        reload=False
    )