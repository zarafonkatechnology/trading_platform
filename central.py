# central_hub.py
"""
CENTRAL HUB - Links All Components Together
Connects: Agents → Risk Manager → Alpha → MT4 → Telegram → Dashboard
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# IMPORTS - CONNECT ALL COMPONENTS
# ============================================================

# Your existing components
from trading_controller import AITradingController, trading_controller
from position_sizing import AdaptivePositionSizer
from alpha_generator import alpha_generator
from performance_dashboard import start_dashboard_server
from mt4_price_provider import get_mt4_prices

# Telegram integration
try:
    from telegram_bot import telegram_bot
except:
    telegram_bot = None
    logger.warning("Telegram bot not available")


class CentralHub:
    """
    Central Command Center - Links ALL components together
    """
    
    def __init__(self):
        logger.info("🏗️ Building Central Hub...")
        
        # ===== COMPONENTS =====
        self.trading_controller = trading_controller
        self.position_sizer = AdaptivePositionSizer()
        self.alpha_generator = alpha_generator
        self.mt4 = get_mt4_prices()
        
        # ===== STATE =====
        self.last_signal = None
        self.last_trade = None
        self.active_trades = {}
        self.trade_history = []
        self.signals = []
        
        # ===== CONFIGURATION =====
        self.config = {
            'min_confidence': 50,
            'max_risk_per_trade': 0.02,  # 2% max risk
            'max_trades_per_day': 10,
            'trades_today': 0,
            'daily_pnl': 0.0,
            'symbols': ['#S&P500', 'EURUSD', 'GBPUSD', 'GOLD', 'SILVER', '#DJ30', 'BRENT_OIL']
        }
        
        # ===== TELEGRAM =====
        self.telegram_bot = telegram_bot
        
        logger.info("✅ Central Hub initialized")
        logger.info(f"   Symbols: {self.config['symbols']}")
        logger.info(f"   Min Confidence: {self.config['min_confidence']}%")
        logger.info(f"   Max Risk: {self.config['max_risk_per_trade']*100}%")
    
    # ============================================================
    # 1. GET SIGNAL FROM AGENTS
    # ============================================================
    
    def get_agent_signal(self, symbol: str) -> Dict:
        """
        Get signal from all agents
        """
        logger.info(f"🔍 Getting signal for {symbol}")
        
        # Use your trading controller's analyze_market
        analysis = self.trading_controller.analyze_market(symbol)
        
        if not analysis:
            return {'action': 'HOLD', 'confidence': 0}
        
        signal = {
            'symbol': symbol,
            'action': analysis.get('action', 'HOLD'),
            'confidence': analysis.get('confidence', 0),
            'reasoning': analysis.get('reasoning', ''),
            'votes': analysis.get('votes', {}),
            'price': analysis.get('price', 0),
            'agent_signals': analysis.get('agent_signals', {}),
            'timestamp': datetime.now().isoformat()
        }
        
        # Store signal history
        self.signals.append(signal)
        self.last_signal = signal
        
        return signal
    
    # ============================================================
    # 2. CALCULATE POSITION SIZE (Risk Manager)
    # ============================================================
    
    def calculate_position(self, symbol: str, signal: Dict) -> Dict:
        """
        Calculate position size using Risk Manager
        """
        logger.info(f"📊 Calculating position size for {symbol}")
        
        confidence = signal.get('confidence', 50) / 100
        
        # Get ATR for volatility adjustment
        try:
            atr = self.mt4._send({"command": "ATR", "symbol": symbol})
            current_atr = atr.get('value', 0.0015) if atr else 0.0015
        except:
            current_atr = 0.0015
        
        # Calculate position
        try:
            result = self.position_sizer.calculate_position(
                win_prob=confidence,
                avg_win=0.02,
                avg_loss=0.01,
                confidence=confidence,
                current_atr=current_atr,
                avg_atr=0.0012,
                regime='TRENDING'
            )
            
            # Get alpha adjustment
            alpha_adjustment = self._get_alpha_adjustment(symbol)
            
            # Apply alpha adjustment
            position = result.get('position_size', 0.01) * (1 + alpha_adjustment)
            
            # Apply risk per trade cap
            account_balance = self._get_account_balance()
            max_risk_amount = account_balance * self.config['max_risk_per_trade']
            max_position = max_risk_amount / (current_atr * 100000)
            
            position = min(position, max_position)
            position = max(position, 0.01)  # Minimum 0.01 lots
            
            return {
                'position_size': round(position, 2),
                'position_percent': round(position / (account_balance / 100000) * 100, 2),
                'components': result.get('components', {}),
                'alpha_adjustment': alpha_adjustment,
                'max_risk': self.config['max_risk_per_trade'] * 100
            }
            
        except Exception as e:
            logger.warning(f"Position sizing error: {e}")
            return {'position_size': 0.01, 'position_percent': 1.0}
    
    def _get_alpha_adjustment(self, symbol: str) -> float:
        """Get alpha adjustment for position sizing"""
        try:
            alphas = self.alpha_generator.generated_alphas
            for alpha in alphas:
                if alpha.get('symbol') == symbol:
                    backtest = alpha.get('backtest', {})
                    win_rate = backtest.get('win_rate', 50)
                    # Alpha adds to position based on win rate
                    return (win_rate - 50) / 100  # -0.5 to +0.5
        except:
            pass
        return 0.0
    
    def _get_account_balance(self) -> float:
        """Get account balance from MT4"""
        try:
            result = self.mt4._send({"command": "ACCOUNT"})
            return result.get('balance', 1000.0)
        except:
            return 1000.0
    
    # ============================================================
    # 3. EXECUTE TRADE
    # ============================================================
    
    def execute_trade(self, symbol: str, signal: Dict, position: Dict) -> bool:
        """
        Execute trade on MT4
        """
        action = signal.get('action')
        price = signal.get('price', 0)
        confidence = signal.get('confidence', 0)
        
        logger.info(f"🚀 EXECUTING {action} on {symbol}")
        logger.info(f"   Confidence: {confidence}%")
        logger.info(f"   Position: {position['position_size']} lots")
        
        if action not in ['BUY', 'SELL']:
            logger.info("⏸️ No action - HOLD")
            return False
        
        if confidence < self.config['min_confidence']:
            logger.info(f"⏸️ Confidence too low: {confidence}% < {self.config['min_confidence']}%")
            return False
        
        # Check daily trade limit
        if self.config['trades_today'] >= self.config['max_trades_per_day']:
            logger.info(f"⏸️ Daily trade limit reached: {self.config['trades_today']}")
            return False
        
        # Get symbol config for SL/TP
        symbol_config = self._get_symbol_config(symbol)
        pip = symbol_config.get('pip', 0.0001)
        sl_pips = symbol_config.get('sl_pips', 20)
        tp_pips = symbol_config.get('tp_pips', 40)
        
        # Calculate SL/TP
        if action == 'BUY':
            sl = price - (sl_pips * pip)
            tp = price + (tp_pips * pip)
        else:
            sl = price + (sl_pips * pip)
            tp = price - (tp_pips * pip)
        
        # Place order
        try:
            result = self.mt4.place_order(
                symbol=symbol,
                order_type=action,
                volume=position['position_size'],
                stop_loss=sl,
                take_profit=tp
            )
            
            if result.get('success'):
                trade = {
                    'symbol': symbol,
                    'action': action,
                    'entry': price,
                    'volume': position['position_size'],
                    'sl': sl,
                    'tp': tp,
                    'confidence': confidence,
                    'reasoning': signal.get('reasoning', ''),
                    'ticket': result.get('ticket'),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.active_trades[symbol] = trade
                self.trade_history.append(trade)
                self.config['trades_today'] += 1
                
                # Send notification
                self._send_notification('trade_executed', trade)
                
                # Update dashboard
                self._update_dashboard('trade_executed', trade)
                
                logger.info(f"✅ Trade executed: {symbol} {action} at {price:.5f}")
                return True
            else:
                logger.error(f"❌ Trade failed: {result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Trade execution error: {e}")
            return False
    
    def _get_symbol_config(self, symbol: str) -> Dict:
        """Get symbol configuration"""
        config = {
            'EURUSD': {'pip': 0.0001, 'sl_pips': 20, 'tp_pips': 40},
            'GBPUSD': {'pip': 0.0001, 'sl_pips': 25, 'tp_pips': 50},
            'USDJPY': {'pip': 0.01, 'sl_pips': 25, 'tp_pips': 50},
            'GOLD': {'pip': 0.1, 'sl_pips': 50, 'tp_pips': 100},
            'SILVER': {'pip': 0.01, 'sl_pips': 50, 'tp_pips': 100},
            '#S&P500': {'pip': 0.1, 'sl_pips': 500, 'tp_pips': 1000},
            '#DJ30': {'pip': 0.1, 'sl_pips': 800, 'tp_pips': 1600},
            '#NASDAQ100': {'pip': 0.1, 'sl_pips': 500, 'tp_pips': 1000},
            'BRENT_OIL': {'pip': 0.01, 'sl_pips': 50, 'tp_pips': 100},
            'CrudeOIL': {'pip': 0.01, 'sl_pips': 50, 'tp_pips': 100},
        }
        return config.get(symbol, {'pip': 0.0001, 'sl_pips': 20, 'tp_pips': 40})
    
    # ============================================================
    # 4. MONITOR TRADES
    # ============================================================
    
    def monitor_trades(self):
        """Monitor active trades"""
        for symbol in list(self.active_trades.keys()):
            trade = self.active_trades[symbol]
            
            # Get current price
            try:
                price_data = self.mt4._send({"command": "PRICE", "symbol": symbol})
                if not price_data:
                    continue
                current_price = price_data.get('bid', 0)
            except:
                continue
            
            if current_price <= 0:
                continue
            
            # Check SL/TP
            if trade['action'] == 'BUY':
                if current_price <= trade['sl']:
                    self._close_trade(symbol, current_price, 'STOP_LOSS')
                elif current_price >= trade['tp']:
                    self._close_trade(symbol, current_price, 'TAKE_PROFIT')
            else:
                if current_price >= trade['sl']:
                    self._close_trade(symbol, current_price, 'STOP_LOSS')
                elif current_price <= trade['tp']:
                    self._close_trade(symbol, current_price, 'TAKE_PROFIT')
    
    def _close_trade(self, symbol: str, price: float, reason: str):
        """Close a trade"""
        if symbol not in self.active_trades:
            return
        
        trade = self.active_trades.pop(symbol)
        
        # Calculate P&L
        if trade['action'] == 'BUY':
            pnl = (price - trade['entry']) * trade['volume'] * 100000
        else:
            pnl = (trade['entry'] - price) * trade['volume'] * 100000
        
        # Update daily P&L
        self.config['daily_pnl'] += pnl
        
        # Add exit info
        trade['exit'] = price
        trade['pnl'] = pnl
        trade['close_reason'] = reason
        
        # Send notification
        self._send_notification('trade_closed', trade)
        self._update_dashboard('trade_closed', trade)
        
        logger.info(f"🔚 Trade closed: {symbol} P&L: ${pnl:.2f} ({reason})")
    
    # ============================================================
    # 5. NOTIFICATIONS (Telegram)
    # ============================================================
    
    def _send_notification(self, event_type: str, data: Dict):
        """Send notification to Telegram"""
        if not self.telegram_bot:
            return
        
        try:
            if event_type == 'trade_executed':
                message = f"""
📊 *TRADE EXECUTED*
━━━━━━━━━━━━━━━━━━━━━
📈 *Symbol:* {data['symbol']}
🎯 *Action:* {data['action']}
💰 *Entry:* {data['entry']:.5f}
🛑 *SL:* {data['sl']:.5f}
✅ *TP:* {data['tp']:.5f}
📊 *Confidence:* {data['confidence']}%
💵 *Volume:* {data['volume']} lots
⏰ *Time:* {data['timestamp'][:19]}
━━━━━━━━━━━━━━━━━━━━━
💡 *Reasoning:* {data.get('reasoning', 'N/A')[:100]}
"""
            elif event_type == 'trade_closed':
                pnl_symbol = "+" if data.get('pnl', 0) > 0 else ""
                message = f"""
🔚 *TRADE CLOSED*
━━━━━━━━━━━━━━━━━━━━━
📊 *Symbol:* {data['symbol']}
📉 *Reason:* {data.get('close_reason', 'N/A')}
💰 *P&L:* {pnl_symbol}${data.get('pnl', 0):.2f}
📈 *Entry:* {data['entry']:.5f}
📉 *Exit:* {data['exit']:.5f}
⏰ *Time:* {data.get('timestamp', '')[:19]}
"""
            else:
                return
            
            self.telegram_bot.send_message(message)
            
        except Exception as e:
            logger.warning(f"Telegram notification error: {e}")
    
    def _update_dashboard(self, event_type: str, data: Dict):
        """Update dashboard"""
        try:
            import requests
            requests.post(
                'http://localhost:5001/api/update',
                json={'type': event_type, 'data': data},
                timeout=2
            )
        except:
            pass
    
    # ============================================================
    # 6. MAIN TRADING CYCLE
    # ============================================================
    
    def run_cycle(self):
        """Run one complete trading cycle"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 Trading Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        # 1. Monitor existing trades
        self.monitor_trades()
        
        # 2. Analyze each symbol
        for symbol in self.config['symbols']:
            # Skip if already have active trade
            if symbol in self.active_trades:
                continue
            
            # Get signal from agents
            signal = self.get_agent_signal(symbol)
            
            if signal['action'] == 'HOLD':
                logger.info(f"⏸️ {symbol}: HOLD")
                continue
            
            # Calculate position size
            position = self.calculate_position(symbol, signal)
            
            # Execute trade
            self.execute_trade(symbol, signal, position)
            
            # Small delay between symbols
            time.sleep(1)
        
        logger.info(f"✅ Cycle complete")
        logger.info(f"   Active trades: {len(self.active_trades)}")
        logger.info(f"   Trades today: {self.config['trades_today']}")
        logger.info(f"   Daily P&L: ${self.config['daily_pnl']:.2f}")
    
    # ============================================================
    # 7. START / STOP
    # ============================================================
    
    def start(self):
        """Start the central hub"""
        logger.info("▶️ Central Hub started")
        
        def loop():
            while True:
                try:
                    self.run_cycle()
                    time.sleep(60)  # Run every minute
                except Exception as e:
                    logger.error(f"❌ Cycle error: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop the central hub"""
        logger.info("⏹️ Central Hub stopped")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔗 CENTRAL HUB - Linking Everything Together")
    print("=" * 60)
    
    # Create hub
    hub = CentralHub()
    
    # Start dashboard in background
    import threading
    dashboard_thread = threading.Thread(
        target=start_dashboard_server,
        args=(5001,),
        daemon=True
    )
    dashboard_thread.start()
    print("📊 Dashboard started on port 5001")
    
    # Start hub
    hub.start()
    
    try:
        while True:
            time.sleep(30)
            status = {
                'active_trades': len(hub.active_trades),
                'trades_today': hub.config['trades_today'],
                'daily_pnl': f"${hub.config['daily_pnl']:.2f}"
            }
            print(f"\n💓 Status: {status}")
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        hub.stop()
        print("✅ Done")