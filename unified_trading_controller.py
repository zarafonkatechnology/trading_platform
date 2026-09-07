"""
UNIFIED TRADING CONTROLLER - Individual Z-Score for ALL Symbols
Each symbol has its own Z-score calculation
"""

import sys
import os
import logging
import time
import json
import math
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import deque

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import core modules
from core.price_service import price_service
from core.risk_manager import RiskManager
from core.signal_service import signal_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================
# INDIVIDUAL Z-SCORE ENGINE (For ALL Symbols)
# ============================================================

class IndividualZScoreEngine:
    """
    Individual Z-Score for each symbol
    Each symbol has its own price history and Z-score calculation
    """
    
    def __init__(self, lookback: int = 50, entry_threshold: float = 2.0, exit_threshold: float = 0.5):
        self.lookback = lookback
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.price_history = {}
        self.mean = {}
        self.std = {}
        self.z_score = {}
        self.samples = {}
        
        # Symbol-specific thresholds (can be overridden)
        self.thresholds = {
            # Indices - Higher volatility, need higher thresholds
            '#NASDAQ100': {'entry': 2.5, 'exit': 0.5},
            '#DJ30': {'entry': 2.5, 'exit': 0.5},
            '#S&P500': {'entry': 2.5, 'exit': 0.5},
            '#RUSS2000': {'entry': 2.5, 'exit': 0.5},
            '#CAC40': {'entry': 2.2, 'exit': 0.5},
            '#DAX40': {'entry': 2.2, 'exit': 0.5},
            '#FTSE100': {'entry': 2.2, 'exit': 0.5},
            '#NIKKEI225': {'entry': 2.2, 'exit': 0.5},
            
            # Metals - Moderate volatility
            'GOLD': {'entry': 2.0, 'exit': 0.5},
            'SILVER': {'entry': 2.0, 'exit': 0.5},
            
            # Energy - Moderate volatility
            'BRENT_OIL': {'entry': 2.0, 'exit': 0.5},
            'CrudeOIL': {'entry': 2.0, 'exit': 0.5},
            
            # Forex Majors - Lower volatility
            'EURUSD': {'entry': 1.8, 'exit': 0.4},
            'GBPUSD': {'entry': 1.8, 'exit': 0.4},
            'USDJPY': {'entry': 1.8, 'exit': 0.4},
            'USDCHF': {'entry': 1.8, 'exit': 0.4},
            'AUDUSD': {'entry': 1.8, 'exit': 0.4},
            'USDCAD': {'entry': 1.8, 'exit': 0.4},
            'NZDUSD': {'entry': 1.8, 'exit': 0.4},
            
            # Forex Crosses
            'EURGBP': {'entry': 1.6, 'exit': 0.4},
            'EURJPY': {'entry': 1.6, 'exit': 0.4},
            'EURCAD': {'entry': 1.6, 'exit': 0.4},
            'EURNZD': {'entry': 1.6, 'exit': 0.4},
            'EURCHF': {'entry': 1.6, 'exit': 0.4},
            
            # Dollar Index
            '#DOLLAR_IND': {'entry': 2.0, 'exit': 0.5}
        }
    
    def get_thresholds(self, symbol: str) -> Tuple[float, float]:
        """Get entry and exit thresholds for a symbol"""
        if symbol in self.thresholds:
            entry = self.thresholds[symbol].get('entry', self.entry_threshold)
            exit_val = self.thresholds[symbol].get('exit', self.exit_threshold)
            return entry, exit_val
        return self.entry_threshold, self.exit_threshold
    
    def update_price(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.lookback)
        self.price_history[symbol].append(price)
        
        # Update samples count
        self.samples[symbol] = len(self.price_history[symbol])
    
    def calculate_zscore(self, symbol: str, price: float) -> Dict:
        """
        Calculate Z-score for a single symbol using its own price history
        """
        # Update price history
        self.update_price(symbol, price)
        
        # Need minimum samples
        if self.samples.get(symbol, 0) < 20:
            return {
                'z_score': 0,
                'action': 'HOLD',
                'confidence': 0,
                'samples': self.samples.get(symbol, 0),
                'reasoning': f'Building history: {self.samples.get(symbol, 0)}/20'
            }
        
        # Calculate mean and std from history
        history = list(self.price_history[symbol])
        self.mean[symbol] = sum(history) / len(history)
        variance = sum((x - self.mean[symbol]) ** 2 for x in history) / len(history)
        self.std[symbol] = math.sqrt(variance) if variance > 0 else 0.0001
        
        # Calculate Z-score
        if self.std[symbol] > 0:
            z_score = (price - self.mean[symbol]) / self.std[symbol]
            self.z_score[symbol] = z_score
        else:
            z_score = 0
        
        # Get symbol-specific thresholds
        entry_threshold, exit_threshold = self.get_thresholds(symbol)
        
        # Generate signal based on Z-score
        if z_score > entry_threshold:
            action = 'SELL'
            confidence = min(95, 75 + (z_score - entry_threshold) * 10)
            reasoning = f"Overbought: Z={z_score:.2f} (threshold: {entry_threshold})"
        elif z_score < -entry_threshold:
            action = 'BUY'
            confidence = min(95, 75 + (-z_score - entry_threshold) * 10)
            reasoning = f"Oversold: Z={z_score:.2f} (threshold: {entry_threshold})"
        elif abs(z_score) < exit_threshold:
            action = 'HOLD'
            confidence = 50
            reasoning = f"Reversion complete: Z={z_score:.2f}"
        else:
            action = 'HOLD'
            confidence = max(40, 50 - abs(z_score) * 5)
            reasoning = f"Normal range: Z={z_score:.2f}"
        
        return {
            'z_score': z_score,
            'action': action,
            'confidence': confidence,
            'mean': self.mean[symbol],
            'std': self.std[symbol],
            'samples': self.samples.get(symbol, 0),
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'reasoning': reasoning,
            'price': price,
            'symbol': symbol
        }


# ============================================================
# DASHBOARD API CLIENT
# ============================================================

class DashboardAPIClient:
    """HTTP client for forex_dashboard.py"""
    
    def __init__(self, url='http://localhost:5002'):
        self.url = url
        self.prices = {}
        self.balance = 0
        self.equity = 0
        self.timestamp = ''
        self.connected = False
        self.last_update = 0
        self.history = {}
        
    def fetch_prices(self):
        """Fetch prices from dashboard API"""
        try:
            response = requests.get(f'{self.url}/api/all_data', timeout=3)
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.connected = True
                    
                    # Parse prices with bid/ask
                    if 'prices' in data:
                        raw_prices = data['prices']
                        self.prices = {}
                        for symbol, price_data in raw_prices.items():
                            if isinstance(price_data, dict):
                                self.prices[symbol] = price_data.get('price', 0)
                            else:
                                self.prices[symbol] = float(price_data) if price_data else 0
                    
                    if 'balance' in data:
                        self.balance = data['balance']
                    if 'equity' in data:
                        self.equity = data['equity']
                    if 'timestamp' in data:
                        self.timestamp = data['timestamp']
                    
                    self.last_update = time.time()
                    return True
                else:
                    self.connected = False
            else:
                self.connected = False
                
        except requests.exceptions.ConnectionError:
            self.connected = False
            logger.debug('Connection error: forex_dashboard.py not running?')
        except Exception as e:
            self.connected = False
            logger.debug(f'Error: {e}')
        
        return False
    
    def get_price(self, symbol: str) -> float:
        """Get price for a symbol"""
        return self.prices.get(symbol, 0)
    
    def get_all_prices(self) -> Dict:
        """Get all prices"""
        return self.prices.copy()
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected


# ============================================================
# UNIFIED TRADING CONTROLLER
# ============================================================

class UnifiedTradingController:
    """Unified Trading Controller with Individual Z-Score for ALL symbols"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # HTTP client
        self.dashboard = DashboardAPIClient()
        
        # Individual Z-Score Engine for ALL symbols
        self.zscore_engine = IndividualZScoreEngine(
            lookback=config.get('zscore_lookback', 50),
            entry_threshold=config.get('zscore_entry', 2.0),
            exit_threshold=config.get('zscore_exit', 0.5)
        )
        
        # Risk Manager
        self.risk_manager = RiskManager(self.config)
        
        # State
        self.is_running = False
        self.cycle_count = 0
        self.cycle_interval = self.config.get('cycle_interval', 5)
        self.all_symbols = price_service.all_symbols
        self.active_positions = {}
        self.trade_history = []
        
        # Connect to dashboard
        print('\n🔌 Connecting to forex_dashboard.py...')
        success = self.dashboard.fetch_prices()
        
        if success:
            print(f'✅ Connected! Received {len(self.dashboard.prices)} prices')
            print(f'   Balance: ${self.dashboard.balance:.2f}')
            print(f'   Timestamp: {self.dashboard.timestamp}')
        else:
            print('❌ Cannot connect to forex_dashboard.py')
            print('   Make sure it\'s running: python forex_dashboard.py')
        
        # Initialize Z-Score engine with initial prices
        if success:
            prices = self.dashboard.get_all_prices()
            for symbol, price in prices.items():
                if price > 0:
                    self.zscore_engine.update_price(symbol, price)
        
        logger.info('=' * 60)
        logger.info('🚀 UNIFIED TRADING CONTROLLER (Individual Z-Score)')
        logger.info('=' * 60)
        logger.info(f'   Total Symbols: {len(self.all_symbols)}')
        logger.info(f'   Each symbol has its own Z-score!')
        logger.info(f'   Dashboard: {"✅ Connected" if success else "❌ Disconnected"}')
        logger.info(f'   Cycle: {self.cycle_interval}s')
        logger.info('=' * 60)
        
        if success:
            self._print_initial_state()
    
    def _print_initial_state(self):
        """Print initial state with Z-score info"""
        prices = self.dashboard.get_all_prices()
        if not prices:
            return
        
        print('\n📊 Initial Z-Score Status:')
        count = 0
        for symbol, price in list(prices.items())[:10]:
            if price > 0:
                # Calculate initial Z-score
                result = self.zscore_engine.calculate_zscore(symbol, price)
                z_score = result.get('z_score', 0)
                samples = result.get('samples', 0)
                status = '✅' if samples >= 20 else f'⏳ {samples}/20'
                print(f'   {symbol}: {price:.5f} | Z={z_score:+.2f} | {status}')
                count += 1
        if len(prices) > 10:
            print(f'   ... and {len(prices) - 10} more')
        print()
    
    def get_price(self, symbol: str) -> float:
        """Get price from dashboard"""
        return self.dashboard.get_price(symbol)
    
    def get_all_prices(self) -> Dict:
        """Get all prices"""
        return self.dashboard.get_all_prices()
    
    # ============================================================
    # SIGNAL GENERATION - INDIVIDUAL Z-SCORE FOR ALL SYMBOLS
    # ============================================================
    
    def get_signal(self, symbol: str) -> Dict:
        """Get trading signal using individual Z-score"""
        price = self.get_price(symbol)
        if price <= 0:
            return {'action': 'HOLD', 'confidence': 0, 'reasoning': 'No price'}
        
        # Calculate individual Z-score for this symbol
        result = self.zscore_engine.calculate_zscore(symbol, price)
        
        # Add extra info
        result['price'] = price
        result['symbol'] = symbol
        result['source'] = 'ZSCORE_SYSTEM'
        result['timestamp'] = datetime.now().isoformat()
        
        # Check if we should enter a trade
        if result['action'] != 'HOLD' and result['confidence'] >= self.config.get('min_confidence', 60):
            # Calculate SL and TP
            config = self.get_symbol_config(symbol)
            pip = config.get('pip', 0.0001)
            sl_pips = config.get('sl_pips', 20)
            tp_pips = config.get('tp_pips', 40)
            
            if result['action'] == 'BUY':
                result['sl'] = price - (sl_pips * pip)
                result['tp'] = price + (tp_pips * pip)
            else:  # SELL
                result['sl'] = price + (sl_pips * pip)
                result['tp'] = price - (tp_pips * pip)
            
            result['volume'] = self.risk_manager.calculate_position_size(
                result['confidence'], 
                result.get('std', 0.02), 
                symbol
            )
        
        return result
    
    # ============================================================
    # SYMBOL CONFIGURATION
    # ============================================================
    
    def get_symbol_config(self, symbol: str) -> Dict:
        """Get configuration for a symbol"""
        configs = {
            # Forex
            'EURUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'GBPUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'USDJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40},
            'USDCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'AUDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'USDCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'NZDUSD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'EURGBP': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25},
            'EURJPY': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40},
            'EURCAD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'EURNZD': {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30},
            'EURCHF': {'pip': 0.0001, 'digits': 5, 'sl_pips': 12, 'tp_pips': 25},
            
            # Indices
            '#NASDAQ100': {'pip': 0.1, 'digits': 2, 'sl_pips': 750, 'tp_pips': 1000},
            '#DJ30': {'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 800},
            '#S&P500': {'pip': 0.1, 'digits': 2, 'sl_pips': 500, 'tp_pips': 750},
            '#RUSS2000': {'pip': 0.1, 'digits': 2, 'sl_pips': 250, 'tp_pips': 500},
            '#CAC40': {'pip': 0.1, 'digits': 2, 'sl_pips': 300, 'tp_pips': 600},
            '#DAX40': {'pip': 0.1, 'digits': 2, 'sl_pips': 400, 'tp_pips': 800},
            '#FTSE100': {'pip': 0.1, 'digits': 2, 'sl_pips': 300, 'tp_pips': 600},
            '#NIKKEI225': {'pip': 0.1, 'digits': 2, 'sl_pips': 400, 'tp_pips': 800},
            
            # Metals
            'GOLD': {'pip': 0.1, 'digits': 2, 'sl_pips': 100, 'tp_pips': 200},
            'SILVER': {'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 100},
            
            # Energy
            'BRENT_OIL': {'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80},
            'CrudeOIL': {'pip': 0.01, 'digits': 2, 'sl_pips': 50, 'tp_pips': 80},
            
            # Dollar
            '#DOLLAR_IND': {'pip': 0.01, 'digits': 3, 'sl_pips': 20, 'tp_pips': 40}
        }
        
        clean_symbol = symbol.replace('#', '')
        if clean_symbol in configs:
            return configs[clean_symbol]
        if symbol in configs:
            return configs[symbol]
        return {'pip': 0.0001, 'digits': 5, 'sl_pips': 15, 'tp_pips': 30}
    
    # ============================================================
    # TRADE EXECUTION
    # ============================================================
    
    def execute_trade(self, symbol: str, signal: Dict) -> Dict:
        """Execute a trade based on signal"""
        action = signal.get('action', 'HOLD')
        confidence = signal.get('confidence', 0)
        price = signal.get('price', 0)
        
        if action == 'HOLD' or confidence < self.config.get('min_confidence', 60):
            return {'status': 'SKIPPED', 'reason': 'Low confidence or HOLD'}
        
        # Check if already have position
        if symbol in self.active_positions:
            return {'status': 'SKIPPED', 'reason': f'Already have position in {symbol}'}
        
        # Check risk limits
        allowed, reason = self.risk_manager.check_trade_allowed(symbol)
        if not allowed:
            return {'status': 'BLOCKED', 'reason': reason}
        
        # Get SL and TP
        sl = signal.get('sl', 0)
        tp = signal.get('tp', 0)
        volume = signal.get('volume', 0.01)
        
        if sl <= 0 or tp <= 0:
            return {'status': 'FAILED', 'reason': 'Invalid SL/TP'}
        
        z_score = signal.get('z_score', 0)
        logger.info(f'\n📊 EXECUTING TRADE:')
        logger.info(f'   Symbol: {symbol}')
        logger.info(f'   Action: {action}')
        logger.info(f'   Price: {price:.5f}')
        logger.info(f'   Volume: {volume:.2f}')
        logger.info(f'   SL: {sl:.5f}')
        logger.info(f'   TP: {tp:.5f}')
        logger.info(f'   Z-Score: {z_score:+.2f}')
        logger.info(f'   Confidence: {confidence:.0f}%')
        
        # ===== SEND ORDER TO MT4 =====
        result = self._send_mt4_order(symbol, action, volume, price, sl, tp)
        
        if result.get('success'):
            # Store position
            self.active_positions[symbol] = {
                'direction': action,
                'entry_price': price,
                'volume': volume,
                'sl': sl,
                'tp': tp,
                'entry_time': datetime.now().isoformat(),
                'z_score': z_score,
                'signal': signal
            }
            
            # Update risk metrics
            self.risk_manager.update_risk_metrics(0, True)
            
            # Save signal
            signal_service.add_signal(
                symbol=symbol,
                signal_type=action,
                confidence=confidence,
                price=price,
                z_score=z_score,
                reasoning=signal.get('reasoning', ''),
                source='ZSCORE_SYSTEM',
                sl=sl,
                tp=tp
            )
            
            logger.info(f'✅ TRADE EXECUTED: {symbol} {action} {volume:.2f} @ {price:.5f}')
            
            return {
                'status': 'EXECUTED',
                'symbol': symbol,
                'action': action,
                'price': price,
                'volume': volume,
                'z_score': z_score,
                'ticket': result.get('ticket', 0)
            }
        
        return {'status': 'FAILED', 'reason': result.get('error', 'Unknown error')}
    
    def _send_mt4_order(self, symbol: str, action: str, volume: float,
                        price: float, sl: float, tp: float) -> Dict:
        """Send order to MT4 via command file"""
        try:
            mt4_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
            command_file = os.path.join(mt4_path, "AI_Commands.txt")
            
            # Format prices based on symbol
            config = self.get_symbol_config(symbol)
            digits = config.get('digits', 5)
            
            order = {
                "command": "ORDER",
                "symbol": symbol,
                "type": action,
                "volume": round(volume, 2),
                "sl": round(sl, digits),
                "tp": round(tp, digits)
            }
            
            with open(command_file, 'w') as f:
                json.dump(order, f)
            
            logger.info(f'📤 ORDER SENT to MT4: {symbol} {action} {volume:.2f} lots')
            
            # Wait for response
            time.sleep(1)
            
            return {'success': True, 'ticket': int(time.time())}
            
        except Exception as e:
            logger.error(f'❌ Order failed: {e}')
            return {'success': False, 'error': str(e)}
    
    # ============================================================
    # POSITION MONITORING
    # ============================================================
    
    def monitor_positions(self):
        """Monitor active positions for SL/TP hits"""
        if not self.active_positions:
            return
        
        prices = self.get_all_prices()
        if not prices:
            return
        
        for symbol in list(self.active_positions.keys()):
            pos = self.active_positions[symbol]
            current_price = prices.get(symbol, 0)
            
            if current_price <= 0:
                continue
            
            # Check SL/TP
            if pos['direction'] == 'BUY':
                if current_price <= pos['sl']:
                    self._close_position(symbol, current_price, 'STOP_LOSS')
                elif current_price >= pos['tp']:
                    self._close_position(symbol, current_price, 'TAKE_PROFIT')
            else:  # SELL
                if current_price >= pos['sl']:
                    self._close_position(symbol, current_price, 'STOP_LOSS')
                elif current_price <= pos['tp']:
                    self._close_position(symbol, current_price, 'TAKE_PROFIT')
    
    def _close_position(self, symbol: str, price: float, reason: str):
        """Close a position"""
        if symbol not in self.active_positions:
            return
        
        pos = self.active_positions.pop(symbol)
        
        # Calculate P&L
        if pos['direction'] == 'BUY':
            pnl = (price - pos['entry_price']) * pos['volume'] * 100000
        else:
            pnl = (pos['entry_price'] - price) * pos['volume'] * 100000
        
        was_win = pnl > 0
        
        # Update risk metrics
        self.risk_manager.update_risk_metrics(pnl, was_win)
        
        # Log
        logger.info(f'🔚 POSITION CLOSED: {symbol}')
        logger.info(f'   P&L: ${pnl:.2f} ({reason})')
        logger.info(f'   Entry: {pos["entry_price"]:.5f} → Exit: {price:.5f}')
        logger.info(f'   Z-Score Entry: {pos.get("z_score", 0):+.2f}')
        
        # Add to history
        self.trade_history.append({
            'symbol': symbol,
            'direction': pos['direction'],
            'entry_price': pos['entry_price'],
            'exit_price': price,
            'pnl': pnl,
            'reason': reason,
            'entry_z_score': pos.get('z_score', 0),
            'exit_time': datetime.now().isoformat()
        })
    
    # ============================================================
    # MAIN CYCLE
    # ============================================================
    def check_zscore_status(self):
        """Debug method to check Z-score status of all symbols"""
        prices = self.dashboard.get_all_prices()
        
        print('\n' + '=' * 60)
        print('📊 Z-SCORE STATUS')
        print('=' * 60)
        print(f'{"Symbol":<15} {"Price":<12} {"Z-Score":<10} {"Samples":<10} {"Signal":<8}')
        print('-' * 60)
        
        for symbol, price in prices.items():
               if price <= 0:
                     continue
               result = self.zscore_engine.calculate_zscore(symbol, price)
               samples = result.get('samples', 0)
               z_score = result.get('z_score', 0)
               action = result.get('action', 'HOLD')
               confidence = result.get('confidence', 0)
               
               # Color coding for signals
               if action != 'HOLD' and confidence >= 60:
                     status = f'🎯 {action}'
               elif samples >= 20:
                     status = '✅ Ready'
               else:
                     status = f'⏳ {samples}/20'
               
               print(f'{symbol:<15} {price:<12.5f} {z_score:+.2f}         {samples:<10} {status:<8}')
        
        print('=' * 60 + '\n')
    def process_cycle(self) -> Dict:
        """Process one trading cycle"""
        self.cycle_count += 1
        
        # Fetch fresh data
        self.dashboard.fetch_prices()
        
        # Monitor positions
        self.monitor_positions()
         # ===== ADD THIS: Check Z-score status every 5 cycles =====
        if self.cycle_count % 5 == 0:
           self.check_zscore_status()
           
        results = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'signals': {},
            'trades': [],
            'active_positions': len(self.active_positions),
            'dashboard_connected': self.dashboard.is_connected()
        }
        
        logger.info(f'\n🔄 CYCLE {self.cycle_count} - {datetime.now().strftime("%H:%M:%S")}')
        logger.info(f'   Dashboard: {"✅ Connected" if self.dashboard.is_connected() else "❌ Disconnected"}')
        logger.info(f'   Active Positions: {len(self.active_positions)}')
        
        # Process each symbol with individual Z-score
        for symbol in self.all_symbols:
            if symbol in self.active_positions:
                continue
            
            # Get signal using individual Z-score
            signal = self.get_signal(symbol)
            results['signals'][symbol] = signal
            
            action = signal.get('action', 'HOLD')
            confidence = signal.get('confidence', 0)
            price = signal.get('price', 0)
            z_score = signal.get('z_score', 0)
            samples = signal.get('samples', 0)
            reasoning = signal.get('reasoning', '')
            
            # Log based on samples
            if samples < 20:
                # Still building history
                if self.cycle_count % 10 == 0:
                    logger.info(f'📊 {symbol}: Building Z-score history {samples}/20')
            elif action != 'HOLD' and confidence >= self.config.get('min_confidence', 60):
                # Trading signal detected
                logger.info(f'🎯 {symbol}: {action} ({confidence:.0f}%) @ {price:.5f} Z={z_score:+.2f} - {reasoning}')
                
                # Execute trade
                trade_result = self.execute_trade(symbol, signal)
                results['trades'].append(trade_result)
                
                if trade_result.get('status') == 'EXECUTED':
                    logger.info(f'✅ {symbol}: TRADE EXECUTED')
                else:
                    logger.info(f'⏸️ {symbol}: {trade_result.get("reason", "Skipped")}')
            else:
                # Show status periodically
                if self.cycle_count % 10 == 0 and price > 0:
                    status = '✅' if samples >= 20 else f'⏳ {samples}/20'
                    logger.info(f'📊 {symbol}: Z={z_score:+.2f} | {status} | {price:.5f}')
        
        # Summary
        risk_status = self.risk_manager.get_status()
        logger.info(f'\n📊 SUMMARY:')
        logger.info(f'   Active Positions: {len(self.active_positions)}')
        logger.info(f'   Daily P&L: ${risk_status["daily_pnl"]:.2f}')
        logger.info(f'   Trades Today: {risk_status["trades_today"]}')
        logger.info(f'   Cold Start: {"Active" if risk_status["cold_start_active"] else "Complete"}')
        
        return results
    
    # ============================================================
    # RUN
    # ============================================================
    
    def run(self):
        """Main loop"""
        self.is_running = True
        logger.info('🚀 Starting Unified Trading Controller...')
        logger.info('   Each symbol has its own Z-score calculation!')
        
        try:
            while self.is_running:
                self.process_cycle()
                time.sleep(self.cycle_interval)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the controller"""
        self.is_running = False
        logger.info('✅ Stopped')


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print('\n' + '=' * 60)
    print('🚀 UNIFIED TRADING CONTROLLER (Individual Z-Score)')
    print('=' * 60)
    
    config = {
        'cycle_interval': 5,
        'min_confidence': 60,
        'daily_loss_limit': 100,
        'max_positions': 3,
        'zscore_lookback': 50,
        'zscore_entry': 2.0,
        'zscore_exit': 0.5,
        'cold_start_threshold': 10,
        'cold_start_min_win_rate': 0.4,
        'max_trades_per_day': 10
    }
    
    controller = UnifiedTradingController(config)
    print('\n✅ Controller ready. Starting...\n')
    
    try:
        controller.run()
    except KeyboardInterrupt:
        print('\n🛑 Stopped by user')
    finally:
        controller.stop()