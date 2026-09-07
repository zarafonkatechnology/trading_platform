# core/order_execution.py - PRODUCTION READY

import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

class OrderExecutionEngine:
    """
    Order Execution Engine for Forex Trading
    Manages order placement, position sizing, and risk management
    """
    
    def __init__(self, engine=None, config: Dict = None):
        self.engine = engine
        self.config = config or {}
        
        # Brokers
        self.brokers = {}
        self.active_orders = []
        self.order_history = []
        
        # Position management
        self.positions = {}
        self.total_exposure = 0
        self.max_position_size = self.config.get('max_position_size', 5)
        self.max_daily_trades = self.config.get('max_daily_trades', 10)
        self.trades_today = 0
        self.daily_pnl = 0.0
        
        # Risk management
        self.risk_per_trade = self.config.get('risk_per_trade', 0.02)
        self.max_daily_loss = self.config.get('max_daily_loss', 0.05)
        self.max_correlation_exposure = self.config.get('max_correlation_exposure', 0.7)
        
        # Monte Carlo reference
        self.monte_carlo = None
        
        # Execution tracking
        self.execution_log = deque(maxlen=1000)
        self.filled_orders = []
        
        # Pair configs
        self.pair_configs = {
            'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03},
            'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03},
            'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03},
            'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03},
            'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25, 'volume': 0.03},
            'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03},
            'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 10, 'tp_pips': 20, 'volume': 0.03},
        }
        
        # Price ranges for validation
        self.price_ranges = {
            'EURUSD': (0.80, 1.60),
            'GBPUSD': (0.90, 1.70),
            'USDJPY': (100, 200),
            'USDCHF': (0.70, 1.20),
            'AUDUSD': (0.50, 0.90),
            'USDCAD': (1.00, 1.70),
            'NZDUSD': (0.40, 0.80),
            'EURGBP': (0.70, 1.00),
            'EURJPY': (100, 200),
            'EURCAD': (1.20, 1.80),
            'EURNZD': (1.50, 2.40),
            'EURCHF': (0.80, 1.20),
        }
        
        logger.info("✅ OrderExecutionEngine initialized")
        logger.info(f"   Max Position Size: {self.max_position_size}")
        logger.info(f"   Risk Per Trade: {self.risk_per_trade*100}%")
        logger.info(f"   Max Daily Loss: {self.max_daily_loss*100}%")
    
    def register_broker(self, pair: str, broker):
        """Register a broker with the execution engine"""
        self.brokers[pair] = broker
        self.positions[pair] = {
            'size': 0,
            'entry_price': 0,
            'current_price': 0,
            'pnl': 0,
            'direction': 'NONE'
        }
        logger.info(f"   Broker registered: {pair}")
    
    def _get_pair_config(self, pair: str) -> Dict:
        """Get configuration for a specific pair."""
        return self.pair_configs.get(pair, {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30, 'volume': 0.03})
    
    def _get_pip(self, pair: str) -> float:
        """Get pip value for a pair."""
        config = self._get_pair_config(pair)
        return config.get('pip', 0.0001)
    
    def _get_sl_pips(self, pair: str) -> float:
        """Get SL pips for a pair."""
        config = self._get_pair_config(pair)
        return config.get('sl_pips', 15)
    
    def _get_atr(self, pair: str, market_data: Dict) -> float:
        """Get ATR for a pair from market data."""
        atr = market_data.get(f'{pair}_atr', 0)
        if atr == 0:
            price = market_data.get(pair, 0)
            atr = price * 0.001 if price > 0 else 0.001
        return atr
    
    def _is_valid_price(self, pair: str, price: float) -> bool:
        """Check if price is within valid range for the pair."""
        if price <= 0:
            return False
        price_range = self.price_ranges.get(pair, (0.01, 10000))
        return price_range[0] < price < price_range[1]
    
    def calculate_position_size(self, pair: str, signal: str, price: float, 
                                confidence: float, account_balance: float,
                                market_data: Dict,
                                risk_per_trade: float = 0.02) -> float:
        """Calculate position size using ATR and Kelly fraction."""
        atr = self._get_atr(pair, market_data)
        if atr is None or atr == 0:
            atr = price * 0.001
        
        pip = self._get_pip(pair)
        sl_pips = self._get_sl_pips(pair)
        stop_distance = sl_pips * pip
        
        base_volume = self.config.get('base_volume', 0.03)
        atr_ratio = atr / (price * 0.001) if price > 0 else 1
        volatility_factor = min(1.0, 0.5 / max(atr_ratio, 0.1))
        confidence_factor = 0.5 + (confidence / 100) * 1.0
        
        kelly = 0.25
        if self.monte_carlo and hasattr(self.monte_carlo, 'last_results'):
            kelly = self.monte_carlo.last_results.get('kelly_fraction', 0.25)
        
        lot_size = base_volume * volatility_factor * confidence_factor * kelly * 2
        lot_size = max(0.01, min(self.max_position_size, round(lot_size, 2)))
        return float(lot_size)
    
    def _update_position_after_execution(self, pair: str, action: str, price: float, volume: float):
        """Update position after order execution."""
        if pair not in self.positions:
            self.positions[pair] = {
                'size': 0,
                'entry_price': 0,
                'current_price': 0,
                'pnl': 0,
                'direction': 'NONE'
            }
        
        position = self.positions[pair]
        
        if action == 'BUY':
            position['size'] += volume
            if position['entry_price'] == 0:
                position['entry_price'] = price
            else:
                total_size = position['size']
                position['entry_price'] = (position['entry_price'] * (total_size - volume) + price * volume) / total_size
            position['direction'] = 'LONG'
        else:
            position['size'] -= volume
            if position['entry_price'] == 0:
                position['entry_price'] = price
            else:
                total_size = abs(position['size'])
                position['entry_price'] = (position['entry_price'] * (total_size + volume) - price * volume) / total_size if total_size > 0 else price
            position['direction'] = 'SHORT'
        
        position['current_price'] = price
        logger.info(f"📊 Position updated: {pair} {action} {volume} @ {price}")
    
    def execute_signal(self, consensus: Dict, market_data: Dict, position_size: float = 1.0, pair: str = None):
        """Execute a trading signal with retry logic and price validation."""
        
        # ===== GET SIGNAL DETAILS =====
        action = consensus.get('signal', 'HOLD')
        confidence = consensus.get('confidence', 0)
        pair = consensus.get('pair') or pair or 'EURUSD'
        
        if action == 'HOLD' or confidence < 50:
            return {'status': 'SKIPPED', 'reason': 'No valid signal'}
        
        # ===== CHECK DAILY LIMITS =====
        if self.trades_today >= self.max_daily_trades:
            return {'status': 'SKIPPED', 'reason': f'Daily trade limit reached ({self.max_daily_trades})'}
        
        if self.daily_pnl < -100:
            return {'status': 'SKIPPED', 'reason': 'Daily loss limit reached'}
        
        # ===== GET PRICE =====
        price = market_data.get(pair, 0)
        if price <= 0 or not self._is_valid_price(pair, price):
            return {'status': 'SKIPPED', 'reason': f'Invalid price for {pair}: {price}'}
        
        # ===== GET CONFIG =====
        config = self._get_pair_config(pair)
        
        pip = config.get('pip', 0.0001)
        digits = config.get('digits', 5)
        sl_pips = config.get('sl_pips', 15)
        tp_pips = config.get('tp_pips', 30)
        volume = config.get('volume', 0.03)
        
        # ===== CALCULATE POSITION SIZE =====
        if position_size > 0:
            volume = volume * position_size
        
        if hasattr(volume, 'item'):
            volume = volume.item()
        volume = float(volume)
        volume = max(volume, 0.01)
        volume = round(volume, 2)
        
        # ===== CALCULATE SL AND TP =====
        if action == 'BUY':
            sl = price - (sl_pips * pip)
            tp = price + (tp_pips * pip)
        else:
            sl = price + (sl_pips * pip)
            tp = price - (tp_pips * pip)
        
        entry_price = round(float(price), digits)
        sl = round(float(sl), digits)
        tp = round(float(tp), digits)
        
        # Validate SL/TP distance (minimum 10 pips)
        min_distance = 10 * pip
        if abs(entry_price - sl) < min_distance:
            if action == 'BUY':
                sl = entry_price - (min_distance * 1.5)
            else:
                sl = entry_price + (min_distance * 1.5)
            sl = round(float(sl), digits)
        
        if abs(tp - entry_price) < min_distance:
            if action == 'BUY':
                tp = entry_price + (min_distance * 2)
            else:
                tp = entry_price - (min_distance * 2)
            tp = round(float(tp), digits)
        
        print(f"\n📤 SENDING ORDER:")
        print(f"   Pair: {pair}")
        print(f"   Action: {action}")
        print(f"   Volume: {volume}")
        print(f"   Entry: {entry_price}")
        print(f"   SL: {sl}")
        print(f"   TP: {tp}")
        
        # ===== SEND TO MT4 WITH RETRY =====
        max_retries = 5
        retry_delay = 1.5
        
        for attempt in range(max_retries):
            try:
                from mt4_price_provider import get_mt4_prices
                mt4 = get_mt4_prices()
                
                if mt4 is None:
                    print(f"   ⚠️ MT4 not available, using market data price")
                    mt4_price_ok = False
                else:
                    # Get fresh price from MT4
                    price_data = mt4._send({"command": "PRICE", "symbol": pair})
                    
                    if price_data and isinstance(price_data, dict):
                        if action == 'BUY':
                            mt4_price = price_data.get('ask', price_data.get('bid', 0))
                        else:
                            mt4_price = price_data.get('bid', price_data.get('ask', 0))
                        
                        # Validate MT4 price
                        if mt4_price and mt4_price > 0 and self._is_valid_price(pair, mt4_price):
                            print(f"   🔄 Fresh MT4 Price: {mt4_price} (valid)")
                            
                            # Use MT4 price for better accuracy
                            if action == 'BUY':
                                sl = mt4_price - (sl_pips * pip)
                                tp = mt4_price + (tp_pips * pip)
                            else:
                                sl = mt4_price + (sl_pips * pip)
                                tp = mt4_price - (tp_pips * pip)
                            
                            entry_price = round(float(mt4_price), digits)
                            sl = round(float(sl), digits)
                            tp = round(float(tp), digits)
                            
                            # Re-validate SL/TP
                            if abs(entry_price - sl) < min_distance:
                                if action == 'BUY':
                                    sl = entry_price - (min_distance * 1.5)
                                else:
                                    sl = entry_price + (min_distance * 1.5)
                                sl = round(float(sl), digits)
                            
                            if abs(tp - entry_price) < min_distance:
                                if action == 'BUY':
                                    tp = entry_price + (min_distance * 2)
                                else:
                                    tp = entry_price - (min_distance * 2)
                                tp = round(float(tp), digits)
                            
                            mt4_price_ok = True
                        else:
                            print(f"   ⚠️ MT4 price {mt4_price} invalid, using market data")
                            mt4_price_ok = False
                    else:
                        print(f"   ⚠️ No price data from MT4, using market data")
                        mt4_price_ok = False
                
                # Add delay between retries
                if attempt > 0:
                    time.sleep(retry_delay * attempt)
                
                # Build order
                order = {
                    "command": "ORDER",
                    "symbol": str(pair),
                    "type": str(action),
                    "volume": float(volume),
                    "sl": float(sl),
                    "tp": float(tp)
                }
                
                # Only send if MT4 is available
                if mt4 is not None:
                    result = mt4._send(order)
                else:
                    result = {'success': False, 'error': 'MT4 not available'}
                
                if result and result.get('success'):
                    print(f"   ✅ ORDER SENT TO MT4!")
                    self.trades_today += 1
                    self._update_position_after_execution(pair, action, entry_price, volume)
                    return {
                        'status': 'EXECUTED',
                        'pair': pair,
                        'action': action,
                        'price': entry_price,
                        'sl': sl,
                        'tp': tp,
                        'volume': volume,
                        'ticket': result.get('ticket', 0)
                    }
                else:
                    error = result.get('error', 'Unknown error') if result else 'No response'
                    error_str = str(error)
                    
                    # Handle specific errors
                    if '4109' in error_str or 'busy' in error_str.lower():
                        print(f"   ⚠️ MT4 busy (attempt {attempt+1}/{max_retries}), retrying in {retry_delay * (attempt + 1):.1f}s...")
                        continue
                    elif 'Timeout' in error_str:
                        print(f"   ⚠️ MT4 timeout (attempt {attempt+1}/{max_retries}), retrying...")
                        time.sleep(retry_delay * 2)
                        continue
                    elif '130' in error_str:
                        print(f"   ⚠️ Invalid stops, increasing SL/TP distance...")
                        sl_pips = config.get('sl_pips', 15) * 2
                        tp_pips = config.get('tp_pips', 30) * 2
                        if action == 'BUY':
                            sl = entry_price - (sl_pips * pip)
                            tp = entry_price + (tp_pips * pip)
                        else:
                            sl = entry_price + (sl_pips * pip)
                            tp = entry_price - (tp_pips * pip)
                        sl = round(float(sl), digits)
                        tp = round(float(tp), digits)
                        continue
                    elif '131' in error_str:
                        print(f"   ⚠️ Invalid volume, reducing to 0.01...")
                        volume = 0.01
                        continue
                    else:
                        print(f"   ❌ ORDER FAILED: {result}")
                        return {
                            'status': 'FAILED',
                            'pair': pair,
                            'action': action,
                            'reason': error_str
                        }
                    
            except Exception as e:
                print(f"   ❌ ORDER ERROR: {e}")
                if attempt < max_retries - 1:
                    print(f"   ⚠️ Retrying ({attempt+1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                return {
                    'status': 'FAILED',
                    'pair': pair,
                    'action': action,
                    'reason': str(e)
                }
        
        return {
            'status': 'FAILED',
            'pair': pair,
            'action': action,
            'reason': f'Max retries ({max_retries}) exceeded'
        }
    
    def _calculate_position_size(self, pair: str, signal: str, price: float, multiplier: float) -> float:
        """Calculate optimal position size based on risk management (legacy)."""
        base_size = 0.1
        confidence = self.config.get('min_confidence', 60)
        confidence_factor = confidence / 100
        volatility_factor = self._get_volatility_factor(pair)
        current_position = self.positions.get(pair, {}).get('size', 0)
        
        size = base_size * confidence_factor * volatility_factor * multiplier
        
        if current_position != 0:
            if (signal == 'BUY' and current_position > 0) or (signal == 'SELL' and current_position < 0):
                size = size * 0.5
            else:
                size = size * 1.2
        
        max_size = self.max_position_size - abs(current_position)
        size = min(size, max_size)
        size = max(0.01, size)
        
        return float(round(size, 2))
    
    def _get_volatility_factor(self, pair: str) -> float:
        """Get volatility factor for position sizing."""
        broker = self.brokers.get(pair)
        if broker and hasattr(broker, 'atr'):
            atr = getattr(broker, 'atr', 0)
            if atr > 0:
                return min(1.0, 0.005 / atr)
        return 1.0
    
    def _check_correlation_limit(self, pair: str) -> bool:
        """Check if adding position would exceed correlation exposure limit."""
        correlated_pairs = []
        
        if pair in ['EURUSD', 'GBPUSD', 'AUDUSD']:
            correlated_pairs = ['EURUSD', 'GBPUSD', 'AUDUSD']
        elif pair in ['USDJPY', 'USDCAD', 'USDCHF']:
            correlated_pairs = ['USDJPY', 'USDCAD', 'USDCHF']
        elif pair in ['EURGBP', 'EURJPY', 'GBPJPY']:
            correlated_pairs = ['EURGBP', 'EURJPY', 'GBPJPY']
        
        total_exposure = 0
        for p in correlated_pairs:
            if p in self.positions:
                total_exposure += abs(self.positions[p].get('size', 0))
        
        if total_exposure >= self.max_correlation_exposure * self.max_position_size:
            return True
        return False
    
    def _create_order(self, pair: str, signal: str, price: float, size: float) -> Dict:
        """Create an order object."""
        return {
            'pair': pair,
            'side': signal,
            'type': 'MARKET',
            'price': price,
            'size': size,
            'timestamp': datetime.now().isoformat(),
            'status': 'PENDING'
        }
    
    def _execute_order(self, order: Dict) -> Dict:
        """Execute an order (simulated)."""
        slippage = 0.0001
        execution_price = order['price'] * (1 + slippage if order['side'] == 'BUY' else 1 - slippage)
        
        return {
            'status': 'FILLED',
            'order_id': f"ORD_{int(time.time())}_{order['pair']}",
            'execution_price': round(execution_price, 4),
            'size': order['size'],
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_position(self, pair: str, order: Dict, execution: Dict):
        """Update position after order execution."""
        if pair not in self.positions:
            self.positions[pair] = {
                'size': 0,
                'entry_price': 0,
                'current_price': 0,
                'pnl': 0,
                'direction': 'NONE'
            }
        
        position = self.positions[pair]
        size = execution['size']
        price = execution['execution_price']
        
        if order['side'] == 'BUY':
            if position['size'] >= 0:
                total_size = position['size'] + size
                position['entry_price'] = (position['entry_price'] * position['size'] + price * size) / total_size if total_size > 0 else price
                position['size'] = total_size
                position['direction'] = 'LONG' if total_size > 0 else 'NONE'
            else:
                position['size'] = position['size'] + size
                if position['size'] > 0:
                    position['entry_price'] = price
                    position['direction'] = 'LONG'
                else:
                    position['direction'] = 'NONE' if position['size'] == 0 else 'SHORT'
        
        elif order['side'] == 'SELL':
            if position['size'] <= 0:
                total_size = position['size'] - size
                position['entry_price'] = (position['entry_price'] * abs(position['size']) + price * size) / (abs(position['size']) + size) if abs(position['size']) + size > 0 else price
                position['size'] = total_size
                position['direction'] = 'SHORT' if total_size < 0 else 'NONE'
            else:
                position['size'] = position['size'] - size
                if position['size'] < 0:
                    position['entry_price'] = price
                    position['direction'] = 'SHORT'
                else:
                    position['direction'] = 'NONE' if position['size'] == 0 else 'LONG'
        
        self.order_history.append({
            'pair': pair,
            'side': order['side'],
            'size': size,
            'price': price,
            'timestamp': datetime.now().isoformat()
        })
        
        logger.info(f"📊 Position updated: {pair} {order['side']} {size} @ {price}")
        logger.info(f"   New Position: {position['direction']} {position['size']} @ {position['entry_price']:.4f}")
    
    def update_pnl(self, market_data: Dict) -> Dict:
        """Update P&L for all positions."""
        total_pnl = 0
        
        for pair, position in self.positions.items():
            if position['size'] != 0:
                current_price = market_data.get(pair, position['current_price'])
                position['current_price'] = current_price
                
                if position['direction'] == 'LONG':
                    pnl = (current_price - position['entry_price']) * position['size']
                elif position['direction'] == 'SHORT':
                    pnl = (position['entry_price'] - current_price) * abs(position['size'])
                else:
                    pnl = 0
                
                position['pnl'] = pnl
                total_pnl += pnl
        
        self.daily_pnl += total_pnl
        
        return {
            'total_pnl': total_pnl,
            'daily_pnl': self.daily_pnl,
            'positions': self.positions
        }
    
    def close_position(self, pair: str) -> Dict:
        """Close a specific position."""
        if pair not in self.positions:
            return {'status': 'ERROR', 'reason': 'Position not found'}
        
        position = self.positions[pair]
        if position['size'] == 0:
            return {'status': 'ERROR', 'reason': 'No position to close'}
        
        side = 'SELL' if position['direction'] == 'LONG' else 'BUY'
        size = abs(position['size'])
        
        order = {
            'pair': pair,
            'side': side,
            'type': 'MARKET',
            'price': position['current_price'],
            'size': size,
            'timestamp': datetime.now().isoformat()
        }
        
        execution = self._execute_order(order)
        
        pnl = position['pnl']
        self.daily_pnl += pnl
        
        self.positions[pair] = {
            'size': 0,
            'entry_price': 0,
            'current_price': 0,
            'pnl': 0,
            'direction': 'NONE'
        }
        
        logger.info(f"📊 Position closed: {pair} {side} {size} @ {execution['execution_price']:.4f}")
        logger.info(f"   P&L: ${pnl:.2f}")
        
        return {
            'status': 'CLOSED',
            'pair': pair,
            'pnl': pnl,
            'execution': execution
        }
    
    def close_all_positions(self) -> List[Dict]:
        """Close all open positions."""
        results = []
        for pair in list(self.positions.keys()):
            if self.positions[pair]['size'] != 0:
                result = self.close_position(pair)
                results.append(result)
        return results
    
    def get_status(self) -> Dict:
        """Get current execution status."""
        return {
            'trades_today': self.trades_today,
            'daily_pnl': self.daily_pnl,
            'active_orders': len(self.active_orders),
            'positions': {
                pair: {
                    'size': pos['size'],
                    'entry_price': pos['entry_price'],
                    'current_price': pos['current_price'],
                    'pnl': pos['pnl'],
                    'direction': pos['direction']
                }
                for pair, pos in self.positions.items() if pos['size'] != 0
            },
            'max_position_size': self.max_position_size,
            'risk_per_trade': self.risk_per_trade,
            'max_daily_trades': self.max_daily_trades
        }
    
    def reset_daily_stats(self):
        """Reset daily statistics."""
        self.trades_today = 0
        self.daily_pnl = 0.0
        logger.info("🔄 Daily stats reset")