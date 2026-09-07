# src/api/routes/spread_routes.py
"""
Spread markup API endpoints - SIMPLIFIED WORKING VERSION
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# SPREAD CONFIGURATION - HARDCODED VALUES
# ============================================================

# Base broker spreads (in pips)
BROKER_SPREADS = {
    # Forex Majors
    'EURUSD': 0.8,
    'GBPUSD': 1.0,
    'USDJPY': 0.9,
    'USDCHF': 1.2,
    'AUDUSD': 1.0,
    'USDCAD': 1.1,
    'NZDUSD': 1.2,
    # Forex Crosses
    'EURGBP': 1.5,
    'EURJPY': 1.5,
    'EURCAD': 1.8,
    'EURNZD': 2.0,
    'EURCHF': 1.8,
    # Metals
    'GOLD': 0.5,
    'SILVER': 0.8,
    # Indices
    '#NASDAQ100': 1.5,
    '#DJ30': 2.0,
    '#S&P500': 1.5,
    '#RUSS2000': 2.5,
    '#CAC40': 2.0,
    '#DAX40': 1.8,
    '#FTSE100': 2.0,
    '#NIKKEI225': 2.0,
    # Energy
    'BRENT_OIL': 3.0,
    'CrudeOIL': 3.0,
}

# Client markup per symbol (in pips)
CLIENT_MARKUP = {
    'EURUSD': 0.5,
    'GBPUSD': 0.5,
    'USDJPY': 0.5,
    'USDCHF': 0.6,
    'AUDUSD': 0.5,
    'USDCAD': 0.6,
    'NZDUSD': 0.6,
    'EURGBP': 0.8,
    'EURJPY': 0.8,
    'EURCAD': 0.9,
    'EURNZD': 1.0,
    'EURCHF': 0.9,
    'GOLD': 0.3,
    'SILVER': 0.5,
    '#NASDAQ100': 0.8,
    '#DJ30': 1.0,
    '#S&P500': 0.8,
    '#RUSS2000': 1.2,
    '#CAC40': 1.0,
    '#DAX40': 0.9,
    '#FTSE100': 1.0,
    '#NIKKEI225': 1.0,
    'BRENT_OIL': 1.5,
    'CrudeOIL': 1.5,
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_client_spread(symbol: str) -> Dict[str, Any]:
    """Get spread for a symbol including markup"""
    # Clean symbol (remove # if needed)
    clean_symbol = symbol.replace('#', '')
    
    # Find the symbol in our configs
    found_symbol = None
    for s in BROKER_SPREADS:
        if s.replace('#', '') == clean_symbol or s == symbol:
            found_symbol = s
            break
    
    if not found_symbol:
        # Return default values if symbol not found
        return {
            'symbol': symbol,
            'broker_spread_pips': 2.0,
            'markup_pips': 0.5,
            'client_spread_pips': 2.5,
            'message': 'Using default values'
        }
    
    broker_spread = BROKER_SPREADS.get(found_symbol, 2.0)
    markup = CLIENT_MARKUP.get(found_symbol, 0.5)
    client_spread = broker_spread + markup
    
    return {
        'symbol': symbol,
        'broker_spread_pips': broker_spread,
        'markup_pips': markup,
        'client_spread_pips': client_spread
    }

def get_all_spreads() -> Dict[str, Dict[str, Any]]:
    """Get all spreads for all symbols"""
    result = {}
    for symbol in BROKER_SPREADS:
        result[symbol] = get_client_spread(symbol)
    return result

# ============================================================
# API ENDPOINTS
# ============================================================

@router.get("/spread/health")
async def spread_health() -> Dict[str, Any]:
    """Health check for spread service"""
    return {
        'success': True,
        'status': 'healthy',
        'symbols_available': len(BROKER_SPREADS),
        'timestamp': datetime.now().isoformat()
    }

@router.get("/spread/client/{symbol}")
async def get_client_spread_endpoint(symbol: str) -> Dict[str, Any]:
    """
    Get client spread with markup for a symbol
    """
    try:
        result = get_client_spread(symbol)
        return {
            'success': True,
            'data': result,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting spread for {symbol}: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.get("/spread/all")
async def get_all_client_spreads() -> Dict[str, Any]:
    """
    Get client spreads for all symbols
    """
    try:
        results = get_all_spreads()
        return {
            'success': True,
            'data': results,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting all spreads: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.get("/spread/symbols")
async def get_spread_symbols() -> Dict[str, Any]:
    """
    Get list of symbols with spreads
    """
    try:
        symbols = []
        for symbol in BROKER_SPREADS:
            symbols.append({
                'symbol': symbol,
                'display_name': symbol.replace('#', '').replace('_', ' '),
                'spread': get_client_spread(symbol)['client_spread_pips']
            })
        
        return {
            'success': True,
            'data': symbols,
            'count': len(symbols),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting spread symbols: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

@router.post("/spread/update/{symbol}")
async def update_spread(
    symbol: str,
    broker_spread: Optional[float] = None,
    markup: Optional[float] = None
) -> Dict[str, Any]:
    """
    Update spread for a symbol
    """
    try:
        # Find the symbol
        found_symbol = None
        for s in BROKER_SPREADS:
            if s.replace('#', '') == symbol.replace('#', '') or s == symbol:
                found_symbol = s
                break
        
        if not found_symbol:
            return {
                'success': False,
                'error': f'Symbol {symbol} not found',
                'timestamp': datetime.now().isoformat()
            }
        
        if broker_spread is not None and broker_spread > 0:
            BROKER_SPREADS[found_symbol] = broker_spread
        
        if markup is not None and markup >= 0:
            CLIENT_MARKUP[found_symbol] = markup
        
        return {
            'success': True,
            'data': {
                'symbol': found_symbol,
                'broker_spread': BROKER_SPREADS[found_symbol],
                'markup': CLIENT_MARKUP[found_symbol],
                'client_spread': BROKER_SPREADS[found_symbol] + CLIENT_MARKUP[found_symbol]
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error updating spread: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }