# src/api/routes/signals.py - Complete Fixed Version

from fastapi import APIRouter, HTTPException, Depends, Body, status
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from src.api.routes.client_auth import get_current_user
from src.database.supabase_client import get_trading_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================
# HEALTH CHECK - Always accessible
# ============================================================

@router.get("/ping")
async def ping_signals():
    """Test endpoint to check if signals router is mounted"""
    return {
        "status": "ok",
        "message": "Signals router is working",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================
# SIGNAL ENDPOINTS - With Authentication
# ============================================================

@router.get("")
@router.get("/")
async def get_signals(
    user: dict = Depends(get_current_user),
    limit: int = 50
):
    """Get signals from database"""
    try:
        logger.info(f"📡 Getting signals for user: {user.get('email')}")
        
        db = get_trading_service()
        
        # Get signals from database
        result = db.client.table('signal_history')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        signals = result.data or []
        
        # Format for frontend
        formatted_signals = []
        for s in signals:
            formatted_signals.append({
                'signal_id': s.get('id'),
                'symbol': s.get('symbol'),
                'type': s.get('signal_type'),
                'confidence': s.get('confidence'),
                'entry_price': s.get('entry_price'),
                'stop_loss': s.get('stop_loss'),
                'take_profit': s.get('take_profit'),
                'reasoning': s.get('reasoning'),
                'source': s.get('source', 'AI'),
                'z_score': s.get('z_score'),
                'created_at': s.get('created_at'),
                'status': s.get('status')
            })
        
        return {
            'success': True,
            'signals': formatted_signals,
            'count': len(formatted_signals),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return {
            'success': False,
            'error': str(e),
            'signals': [],
            'count': 0
        }


@router.get("/all")
async def get_all_signals(
    user: dict = Depends(get_current_user)
):
    """Get all signals from database"""
    try:
        db = get_trading_service()
        
        result = db.client.table('signal_history')\
            .select('*')\
            .order('created_at', desc=True)\
            .limit(100)\
            .execute()
        
        signals = result.data or []
        
        return {
            'success': True,
            'signals': signals,
            'count': len(signals),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'signals': [],
            'count': 0
        }


@router.get("/stats")
async def get_signal_stats(
    user: dict = Depends(get_current_user)
):
    """Get signal statistics"""
    try:
        db = get_trading_service()
        
        # Get all signals
        result = db.client.table('signal_history').select('*').execute()
        signals = result.data or []
        
        # Count by type
        buy_count = sum(1 for s in signals if s.get('signal_type') == 'BUY')
        sell_count = sum(1 for s in signals if s.get('signal_type') == 'SELL')
        hold_count = sum(1 for s in signals if s.get('signal_type') == 'HOLD')
        
        # Count by status
        pending = sum(1 for s in signals if s.get('status') == 'PENDING')
        executed = sum(1 for s in signals if s.get('status') == 'EXECUTED')
        
        # Count by source
        source_counts = {}
        for s in signals:
            source = s.get('source', 'Unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            'success': True,
            'stats': {
                'total_signals': len(signals),
                'last_update': datetime.now().isoformat(),
                'signals_by_type': {
                    'BUY': buy_count,
                    'SELL': sell_count,
                    'HOLD': hold_count
                },
                'signals_by_status': {
                    'PENDING': pending,
                    'EXECUTED': executed
                },
                'signals_by_source': source_counts
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/generate")
async def generate_test_signal(
    user: dict = Depends(get_current_user)
):
    """Generate a test signal (for testing)"""
    try:
        logger.info(f"📡 Generating test signal for user: {user.get('email')}")
        
        db = get_trading_service()
        
        new_signal = {
            'symbol': 'EURUSD',
            'signal_type': 'BUY',
            'confidence': 85,
            'entry_price': 1.14337,
            'stop_loss': 1.14000,
            'take_profit': 1.15000,
            'reasoning': 'Test signal generated manually',
            'source': 'Test_Manual',
            'z_score': 2.5,
            'timeframe': 'M15',
            'status': 'PENDING',
            'executed': False,
            'created_at': datetime.now().isoformat()
        }
        
        result = db.client.table('signal_history')\
            .insert(new_signal)\
            .execute()
        
        if result.data:
            signal = result.data[0]
            logger.info(f"✅ Test signal generated: ID={signal.get('id')}")
            return {
                'success': True,
                'signal': signal,
                'message': 'Test signal generated and saved to database'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to save signal'
            }
    except Exception as e:
        logger.error(f"Error generating test signal: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/subscribe")
async def subscribe_to_signals(
    symbols: List[str] = Body(..., embed=False),
    user: dict = Depends(get_current_user)
):
    """Subscribe to signals"""
    try:
        user_id = str(user.get('id'))
        return {
            'success': True,
            'message': f'Subscribed to {len(symbols)} symbols',
            'symbols': symbols
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@router.post("/unsubscribe")
async def unsubscribe_from_signals(
    user: dict = Depends(get_current_user)
):
    """Unsubscribe from signals"""
    try:
        return {
            'success': True,
            'message': 'Unsubscribed from all signals'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }