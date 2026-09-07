"""
ZeroMQ Bridge for MetaTrader 4
Connects your AI agents to MT4 for live trading
"""

import zmq
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MT4Bridge:
    """
    ZeroMQ bridge between Python agents and MetaTrader 4.
    
    Architecture:
    [Python Agents] --(ZeroMQ)--> [MT4 EA] --> [Broker]
    
    Commands:
    - PING: Check connection
    - PRICE: Get current price
    - BUY: Execute market buy order
    - SELL: Execute market sell order
    - CLOSE: Close position
    - MODIFY: Modify stop loss / take profit
    - POSITIONS: Get open positions
    - ACCOUNT: Get account info
    """
    
    def __init__(self, zmq_port: int = 5555, mt4_port: int = 5556):
        self.zmq_port = zmq_port  # Port for sending commands to MT4
        self.mt4_port = mt4_port  # Port for receiving responses
        self.context = zmq.Context()
        self.socket = None
        self.is_connected = False
        self.response_timeout = 5  # seconds
        
        # Statistics
        self.commands_sent = 0
        self.commands_succeeded = 0
        self.commands_failed = 0
        
    def connect(self) -> bool:
        """Establish connection to MT4 EA"""
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(f"tcp://localhost:{self.zmq_port}")
            self.socket.setsockopt(zmq.RCVTIMEO, self.response_timeout * 1000)
            self.is_connected = True
            logger.info(f"✅ Connected to MT4 on port {self.zmq_port}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to MT4: {e}")
            return False
    
    def _send_command(self, command: Dict) -> Dict:
        """Send command to MT4 and wait for response"""
        if not self.is_connected:
            if not self.connect():
                return {'error': 'Not connected to MT4'}
        
        self.commands_sent += 1
        
        try:
            self.socket.send_json(command)
            response = self.socket.recv_json()
            self.commands_succeeded += 1
            return response
        except zmq.Again:
            self.commands_failed += 1
            logger.error(f"Timeout waiting for MT4 response")
            return {'error': 'Timeout - MT4 not responding'}
        except Exception as e:
            self.commands_failed += 1
            logger.error(f"Command error: {e}")
            return {'error': str(e)}
    
    def ping(self) -> bool:
        """Check if MT4 is responding"""
        response = self._send_command({'command': 'PING'})
        return response.get('status') == 'OK'
    
    def get_price(self, symbol: str) -> Dict:
        """Get current bid/ask price for symbol"""
        response = self._send_command({
            'command': 'PRICE',
            'symbol': symbol
        })
        return response
    
    def buy(self, symbol: str, volume: float, 
            stop_loss: float = None, take_profit: float = None,
            comment: str = "AI_Agent") -> Dict:
        """Execute a market BUY order"""
        order = {
            'command': 'BUY',
            'symbol': symbol,
            'volume': volume,
            'comment': comment
        }
        if stop_loss:
            order['stop_loss'] = stop_loss
        if take_profit:
            order['take_profit'] = take_profit
        
        response = self._send_command(order)
        
        if response.get('success'):
            logger.info(f"✅ BUY {volume} {symbol} at {response.get('price')}")
        else:
            logger.error(f"❌ BUY failed: {response.get('error')}")
        
        return response
    
    def sell(self, symbol: str, volume: float, 
             stop_loss: float = None, take_profit: float = None,
             comment: str = "AI_Agent") -> Dict:
        """Execute a market SELL order"""
        order = {
            'command': 'SELL',
            'symbol': symbol,
            'volume': volume,
            'comment': comment
        }
        if stop_loss:
            order['stop_loss'] = stop_loss
        if take_profit:
            order['take_profit'] = take_profit
        
        response = self._send_command(order)
        
        if response.get('success'):
            logger.info(f"✅ SELL {volume} {symbol} at {response.get('price')}")
        else:
            logger.error(f"❌ SELL failed: {response.get('error')}")
        
        return response
    
    def close_position(self, ticket: int) -> Dict:
        """Close a position by ticket number"""
        response = self._send_command({
            'command': 'CLOSE',
            'ticket': ticket
        })
        return response
    
    def modify_position(self, ticket: int, stop_loss: float = None, 
                        take_profit: float = None) -> Dict:
        """Modify stop loss / take profit of a position"""
        order = {'command': 'MODIFY', 'ticket': ticket}
        if stop_loss:
            order['stop_loss'] = stop_loss
        if take_profit:
            order['take_profit'] = take_profit
        
        response = self._send_command(order)
        return response
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        response = self._send_command({'command': 'POSITIONS'})
        return response.get('positions', [])
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        response = self._send_command({'command': 'ACCOUNT'})
        return response
    
    def get_stats(self) -> Dict:
        """Get bridge statistics"""
        return {
            'connected': self.is_connected,
            'commands_sent': self.commands_sent,
            'commands_succeeded': self.commands_succeeded,
            'commands_failed': self.commands_failed,
            'success_rate': round(self.commands_succeeded / max(1, self.commands_sent) * 100, 1)
        }


# ============================================================
# Integration with Your Existing Agents
# ============================================================

class MT4TradingIntegration:
    """
    Integrates MT4 bridge with your existing agent system
    """
    
    def __init__(self, zmq_port: int = 5555):
        self.bridge = MT4Bridge(zmq_port=zmq_port)
        self.auto_trade_enabled = False
        self.max_risk_per_trade = 0.02  # 2% max risk
        self.order_history = []
        
    def start(self):
        """Start the MT4 bridge connection"""
        if self.bridge.connect():
            logger.info("🚀 MT4 Bridge ready for live trading")
            return True
        return False
    
    def execute_signal(self, signal: Dict) -> Dict:
        """
        Execute a trading signal from your agents
        
        signal should contain:
        - asset: symbol (e.g., 'EURUSD')
        - action: 'BUY' or 'SELL'
        - entry_price: suggested entry
        - stop_loss: stop loss price
        - take_profit: take profit price
        - confidence: agent confidence (0-100)
        - position_size: percentage of capital (0-1)
        """
        
        if not self.auto_trade_enabled:
            return {'error': 'Auto trading disabled', 'signal': signal}
        
        # Calculate position size based on risk
        account = self.bridge.get_account_info()
        if account.get('error'):
            return {'error': 'Cannot get account info'}
        
        balance = account.get('balance', 10000)
        risk_amount = balance * self.max_risk_per_trade
        
        # Calculate position size
        entry = signal.get('entry_price')
        stop = signal.get('stop_loss')
        if entry and stop:
            risk_per_unit = abs(entry - stop)
            if risk_per_unit > 0:
                size = risk_amount / risk_per_unit
            else:
                size = 1000  # Default
        else:
            size = 1000
        
        # Apply confidence multiplier
        confidence = signal.get('confidence', 50)
        size = size * (confidence / 100)
        
        # Round to valid lot size
        size = round(size / 1000) * 1000
        size = max(1000, min(100000, size))  # Min 0.01 lot, Max 1 lot
        
        # Execute order
        if signal.get('action') == 'BUY':
            result = self.bridge.buy(
                symbol=signal['asset'],
                volume=size,
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                comment=f"AI_{signal.get('strategy', 'MOMENTUM')}"
            )
        else:
            result = self.bridge.sell(
                symbol=signal['asset'],
                volume=size,
                stop_loss=signal.get('stop_loss'),
                take_profit=signal.get('take_profit'),
                comment=f"AI_{signal.get('strategy', 'MOMENTUM')}"
            )
        
        # Record order
        self.order_history.append({
            'timestamp': datetime.now().isoformat(),
            'signal': signal,
            'result': result,
            'size': size
        })
        
        return result
    
    def get_status(self) -> Dict:
        """Get bridge status"""
        return {
            'connected': self.bridge.is_connected,
            'auto_trade_enabled': self.auto_trade_enabled,
            'bridge_stats': self.bridge.get_stats(),
            'orders_today': len([o for o in self.order_history 
                                if o['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d'))])
        }


# Global instance
mt4_integration = MT4TradingIntegration()
