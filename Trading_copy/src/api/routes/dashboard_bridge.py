# src/api/routes/dashboard_bridge.py
"""
Dashboard bridge routes - connects to existing forex dashboard
"""

from fastapi import APIRouter, HTTPException
import requests
import json
import os
from datetime import datetime
from typing import Dict, Any

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Path to dashboard data file
DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
DASHBOARD_URL = "http://localhost:5002/api/all_data"

@router.get("/data")
async def get_dashboard_data():
    """Fetch data from existing dashboard and do not fallback to files."""
    try:
        try:
            response = requests.get(DASHBOARD_URL, timeout=3)
            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "dashboard_api",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Dashboard API unavailable: {str(e)}"
            )

        raise HTTPException(
            status_code=503,
            detail="Dashboard API unavailable and file fallback is disabled"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard data: {str(e)}"
        )

@router.get("/prices")
async def get_prices():
    """Get current prices from dashboard"""
    try:
        result = await get_dashboard_data()
        return {
            "prices": result.get("data", {}).get("prices", {}),
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get prices: {str(e)}"
        )

@router.get("/account")
async def get_account_info():
    """Get account information"""
    try:
        result = await get_dashboard_data()
        data = result.get("data", {})
        return {
            "balance": data.get("balance", 0),
            "equity": data.get("equity", 0),
            "profit": data.get("profit", 0),
            "margin": data.get("margin", 0),
            "free_margin": data.get("free_margin", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get account info: {str(e)}"
        )

@router.get("/leaderboard")
async def get_leaderboard():
    """Get leaderboard data"""
    try:
        # Try to read leaderboard file
        leaderboard_file = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/leaderboard.json"
        if os.path.exists(leaderboard_file):
            with open(leaderboard_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return {"leaderboard": data}
                elif isinstance(data, dict) and 'leaderboard' in data:
                    return {"leaderboard": data['leaderboard']}
        
        # Try to get from dashboard
        result = await get_dashboard_data()
        data = result.get("data", {})
        if "leaderboard" in data:
            return {"leaderboard": data["leaderboard"]}
        
        return {"leaderboard": []}
        
    except Exception as e:
        return {"leaderboard": [], "error": str(e)}