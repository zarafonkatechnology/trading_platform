# src/api/routes/master_dashboard.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================
# DUMMY FUNCTIONS FOR DEVELOPMENT (Replace with real DB calls)
# ============================================================

async def get_master_user():
    """Get master user from JWT token"""
    # In production, this would validate JWT token
    return {
        'id': 'master_1',
        'email': 'admin@nexus.com',
        'role': 'admin'
    }

async def get_all_clients():
    """Get all clients from database"""
    # In production, this would query Supabase
    return [
        {'id': 'client_1', 'name': 'Trader A'},
        {'id': 'client_2', 'name': 'Trader B'},
        {'id': 'client_3', 'name': 'Trader C'},
    ]

async def get_account(client_id: str):
    """Get account details for a client"""
    # In production, this would query Supabase
    return {
        'balance': 997911.08,
        'equity': 997773.08,
        'used_margin': 6659.80,
        'free_margin': 991113.28,
        'margin_level': 14982.0,
        'position_size': 1.0,
        'client_name': 'Trader A'
    }

async def get_open_positions(client_id: str):
    """Get open positions for a client"""
    # In production, this would query Supabase
    return []

async def calculate_total_pnl(client_id: str) -> float:
    """Calculate total P&L for a client"""
    # In production, this would sum all position P&L
    return -138.00

async def get_risk_tolerance(client_id: str):
    """Get client's risk tolerance"""
    return {'max_risk': 0.02}  # 2% risk per trade

async def get_client_win_rate(client_id: str):
    """Get client's win rate"""
    return 45.0

async def get_atr(symbol: str):
    """Get Average True Range for symbol"""
    return 0.0015

# ============================================================
# MASTER DASHBOARD - AGGREGATE VIEW
# ============================================================

@router.get("/dashboard")
async def get_master_dashboard(user: dict = Depends(get_master_user)):
    """Get aggregated dashboard for all clients"""
    
    try:
        clients = await get_all_clients()
        total_clients = len(clients)
        
        # Aggregate metrics
        total_balance = 0
        total_equity = 0
        total_used_margin = 0
        total_free_margin = 0
        total_pnl = 0
        active_trades = 0
        
        at_risk_clients = []
        margin_call_clients = []
        client_summaries = []
        
        for client in clients:
            account = await get_account(client['id'])
            positions = await get_open_positions(client['id'])
            
            # Calculate P&L
            pnl = await calculate_total_pnl(client['id'])
            
            total_balance += account['balance']
            total_equity += account['equity']
            total_used_margin += account['used_margin']
            total_free_margin += account['free_margin']
            total_pnl += pnl
            active_trades += len(positions)
            
            # Risk monitoring
            if account['margin_level'] < 150:
                at_risk_clients.append({
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'margin_level': account['margin_level'],
                    'equity': account['equity'],
                    'used_margin': account['used_margin']
                })
            
            if account['margin_level'] < 100:
                margin_call_clients.append({
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'margin_level': account['margin_level'],
                    'equity': account['equity'],
                    'used_margin': account['used_margin']
                })
            
            # Client summary for table
            client_summaries.append({
                'client_id': client['id'],
                'client_name': client['name'],
                'balance': account['balance'],
                'equity': account['equity'],
                'pnl': pnl,
                'margin_level': account['margin_level'],
                'positions': len(positions)
            })
        
        return {
            'success': True,
            'summary': {
                'total_clients': total_clients,
                'total_balance': round(total_balance, 2),
                'total_equity': round(total_equity, 2),
                'total_used_margin': round(total_used_margin, 2),
                'total_free_margin': round(total_free_margin, 2),
                'total_pnl': round(total_pnl, 2),
                'active_trades': active_trades,
                'clients_at_risk': len(at_risk_clients),
                'margin_call_clients': len(margin_call_clients)
            },
            'at_risk_clients': at_risk_clients,
            'margin_call_clients': margin_call_clients,
            'client_summaries': client_summaries,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in master dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# RISK ALERTS
# ============================================================

@router.get("/risk/alerts")
async def get_risk_alerts(user: dict = Depends(get_master_user)):
    """Get all risk alerts for monitoring"""
    
    try:
        alerts = []
        
        # Check all clients for risk
        clients = await get_all_clients()
        
        for client in clients:
            account = await get_account(client['id'])
            
            if account['margin_level'] < 50:
                alerts.append({
                    'type': 'STOP_OUT_RISK',
                    'severity': 'CRITICAL',
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'margin_level': account['margin_level'],
                    'message': f"Stop out risk! Margin level: {account['margin_level']:.0f}%"
                })
            elif account['margin_level'] < 100:
                alerts.append({
                    'type': 'MARGIN_CALL',
                    'severity': 'HIGH',
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'margin_level': account['margin_level'],
                    'message': f"Margin call! Margin level: {account['margin_level']:.0f}%"
                })
            elif account['margin_level'] < 150:
                alerts.append({
                    'type': 'LOW_MARGIN',
                    'severity': 'MEDIUM',
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'margin_level': account['margin_level'],
                    'message': f"Low margin: {account['margin_level']:.0f}%"
                })
        
        return {
            'success': True,
            'alerts': alerts,
            'count': len(alerts),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in risk alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# POSITION SIZING RECOMMENDATIONS
# ============================================================

@router.get("/recommendations/{client_id}")
async def get_position_recommendations(
    client_id: str, 
    user: dict = Depends(get_master_user)
):
    """Get position sizing recommendations for a client"""
    
    try:
        account = await get_account(client_id)
        
        # Calculate recommended position size
        # Kelly Criterion approach
        win_rate = await get_client_win_rate(client_id)
        risk_reward = 1.5  # Typical 1.5:1
        
        kelly_fraction = win_rate - (1 - win_rate) / risk_reward
        kelly_fraction = max(0, min(0.25, kelly_fraction))  # Cap at 25%
        
        # Risk per trade (2% of equity)
        risk_per_trade = account['equity'] * 0.02
        
        # Position size based on volatility
        atr = await get_atr('EURUSD')
        pip_value = 10  # $10 per pip per lot
        
        # Recommended lot size
        recommended_lots = risk_per_trade / (atr * pip_value * 100)  # Adjust for pips
        recommended_lots = round(max(0.01, min(10, recommended_lots)), 2)
        
        # Maximum position size (50% of free margin)
        max_position_size = (account['free_margin'] * 0.5) / 1000
        max_position_size = round(max(0.01, min(10, max_position_size)), 2)
        
        # Get current positions
        positions = await get_open_positions(client_id)
        current_volume = sum(pos.get('volume', 0) for pos in positions)
        
        return {
            'success': True,
            'client_id': client_id,
            'recommendations': {
                'kelly_fraction': round(kelly_fraction * 100, 1),
                'risk_per_trade': round(risk_per_trade, 2),
                'recommended_lots': recommended_lots,
                'max_position_size': max_position_size,
                'current_position_size': current_volume,
                'confidence': 'HIGH' if win_rate > 50 else 'MEDIUM'
            },
            'risk_metrics': {
                'win_rate': win_rate,
                'current_margin_level': account['margin_level'],
                'free_margin': account['free_margin'],
                'equity': account['equity']
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in position recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# CLIENT PERFORMANCE
# ============================================================

@router.get("/client/{client_id}/performance")
async def get_client_performance(
    client_id: str,
    period: str = "30d",
    user: dict = Depends(get_master_user)
):
    """Get performance details for a specific client"""
    
    try:
        # Get client data
        account = await get_account(client_id)
        positions = await get_open_positions(client_id)
        
        # Calculate performance metrics
        pnl = await calculate_total_pnl(client_id)
        win_rate = await get_client_win_rate(client_id)
        
        # Get trade history (in production, from database)
        trades = []  # Would be from database
        
        return {
            'success': True,
            'client_id': client_id,
            'account': account,
            'performance': {
                'total_pnl': round(pnl, 2),
                'win_rate': round(win_rate, 2),
                'open_positions': len(positions),
                'total_trades': len(trades),
                'risk_score': self._calculate_risk_score(account)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in client performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _calculate_risk_score(account: dict) -> int:
    """Calculate risk score (0-100)"""
    score = 0
    
    if account['margin_level'] > 500:
        score += 30
    elif account['margin_level'] > 200:
        score += 20
    else:
        score += 5
    
    if account['free_margin'] / account['equity'] > 0.5:
        score += 20
    
    if account['used_margin'] < 1000:
        score += 10
    
    return min(100, score)