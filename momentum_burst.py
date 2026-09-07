"""
Momentum Burst Strategy - Fast Trading for Nasdaq, Gold, CrudeOIL
- Detects sudden volume + price acceleration
- 1-5 minute hold times
- Tight stops with 1:2 risk-reward
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import threading
import time


class MomentumBurstDetector:
    """
    Detects momentum burst conditions:
    - Price acceleration > 0.15% in 1 minute
    - Volume spike > 2x average
    - Confirmation from multiple timeframes
    """
    
    def __init__(self, 
                 price_change_threshold: float = 0.0015,  # 0.15%
                 volume_ratio_threshold: float = 2.0,     # 2x average
                 lookback_minutes: int = 10,
                 acceleration_window: int = 5):           # 5 periods
        
        self.price_change_threshold = price_change_threshold
        self.volume_ratio_threshold = volume_ratio_threshold
        self.lookback_minutes = lookback_minutes
        self.acceleration_window = acceleration_window
        
        # Price history per asset
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        
        # Asset-specific volatility multipliers
        self.asset_multipliers = {
            'NAS100/USD': 1.2,   # More volatile, adjust threshold
            'XAU/USD': 0.8,      # Less volatile
            'BCO/USD': 1.0,      # Standard
            'S&P500/USD': 0.9,
            'DJ30/USD': 0.9
        }
def calculate_momentum_strength(self, price_change_pct: float, volume_ratio: float) -> float:
    """Calculate momentum strength (0-100)"""
    
    # Price change contribution (max 70 points)
    if price_change_pct > 0:
        price_strength = min(70, price_change_pct * 50)  # 1.23% * 50 = 61.5
    else:
        price_strength = min(70, abs(price_change_pct) * 50)
    
    # Volume contribution (max 30 points)
    if volume_ratio > 3.0:
        volume_strength = 30
    elif volume_ratio > 2.0:
        volume_strength = 20
    elif volume_ratio > 1.5:
        volume_strength = 15
    elif volume_ratio > 1.2:
        volume_strength = 10
    else:
        volume_strength = 0
    
    total_strength = price_strength + volume_strength
    
    # Adjust for direction alignment
    # (This would be passed from the action)
    
    return min(100, total_strength)
def update_price(self, asset: str, price: float, volume: float, timestamp: datetime = None):
        """Update price and volume history"""
        if asset not in self.price_history:
            self.price_history[asset] = deque(maxlen=100)
            self.volume_history[asset] = deque(maxlen=100)
        
        self.price_history[asset].append({
            'price': price,
            'timestamp': timestamp or datetime.now()
        })
        self.volume_history[asset].append({
            'volume': volume,
            'timestamp': timestamp or datetime.now()
        })
    
def get_rolling_returns(self, asset: str, window_minutes: int = 1) -> float:
        """Calculate rolling return over specified window"""
        if asset not in self.price_history or len(self.price_history[asset]) < window_minutes:
            return 0.0
        
        # Get prices within time window
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [p for p in self.price_history[asset] if p['timestamp'] >= cutoff]
        
        if len(recent) < 2:
            return 0.0
        
        start_price = recent[0]['price']
        end_price = recent[-1]['price']
        
        return (end_price - start_price) / start_price
    
def get_volume_ratio(self, asset: str) -> float:
        """Calculate current volume vs average"""
        if asset not in self.volume_history or len(self.volume_history[asset]) < 10:
            return 1.0
        
        current_volume = self.volume_history[asset][-1]['volume']
        avg_volume = np.mean([v['volume'] for v in list(self.volume_history[asset])[-10:]])
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
def get_price_acceleration(self, asset: str) -> float:
        """Calculate price acceleration (change of rate of change)"""
        if asset not in self.price_history or len(self.price_history[asset]) < self.acceleration_window + 2:
            return 0.0
        
        prices = [p['price'] for p in list(self.price_history[asset])[-self.acceleration_window:]]
        
        if len(prices) < 3:
            return 0.0
        
        # Calculate velocities
        velocities = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        if len(velocities) < 2:
            return 0.0
        
        # Acceleration = change in velocity
        acceleration = (velocities[-1] - velocities[-2]) / (velocities[-2] + 1e-10)
        
        return acceleration
    
def detect_momentum_burst(self, asset: str) -> Tuple[bool, str, float, Dict]:
        """
        Detect if a momentum burst is occurring.
        
        Returns:
            (is_burst, direction, confidence, details)
        """
        multiplier = self.asset_multipliers.get(asset, 1.0)
        threshold = self.price_change_threshold * multiplier
        
        # Calculate metrics
        return_1min = self.get_rolling_returns(asset, window_minutes=1)
        return_3min = self.get_rolling_returns(asset, window_minutes=3)
        volume_ratio = self.get_volume_ratio(asset)
        acceleration = self.get_price_acceleration(asset)
        
        # Determine direction
        is_bullish = return_1min > 0 and return_3min > 0
        is_bearish = return_1min < 0 and return_3min < 0
        
        # Check conditions
        price_condition = abs(return_1min) > threshold
        volume_condition = volume_ratio > self.volume_ratio_threshold
        acceleration_condition = abs(acceleration) > 0.5  # Strong acceleration
        
        conditions_met = sum([price_condition, volume_condition, acceleration_condition])
        
        if conditions_met >= 2 and (is_bullish or is_bearish):
            direction = 'BUY' if is_bullish else 'SELL'
            confidence = 60 + (conditions_met * 10) + min(20, volume_ratio * 10)
            confidence = min(95, confidence)
            
            details = {
                'return_1min': round(return_1min * 100, 2),
                'return_3min': round(return_3min * 100, 2),
                'volume_ratio': round(volume_ratio, 1),
                'acceleration': round(acceleration, 2),
                'conditions_met': conditions_met,
                'asset_multiplier': multiplier
            }
            
            return True, direction, confidence, details
        
        return False, 'HOLD', 0, {}
    
def calculate_risk_levels(self, asset: str, price: float, direction: str) -> Dict:
        """Calculate tight stops for momentum burst trades"""
        # Get ATR-like measure from recent volatility
        if asset in self.price_history and len(self.price_history[asset]) > 10:
            prices = [p['price'] for p in list(self.price_history[asset])[-10:]]
            volatility = np.std(prices) / np.mean(prices)
        else:
            volatility = 0.005  # Default 0.5%
        
        # Tighter stops for momentum trades
        if direction == 'BUY':
            stop_loss = price * (1 - volatility * 1.5)
            take_profit_1 = price * (1 + volatility * 2.5)
            take_profit_2 = price * (1 + volatility * 4.0)
        else:
            stop_loss = price * (1 + volatility * 1.5)
            take_profit_1 = price * (1 - volatility * 2.5)
            take_profit_2 = price * (1 - volatility * 4.0)
        
        # Max hold time for momentum bursts
        max_hold_minutes = 5
        
        return {
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'max_hold_minutes': max_hold_minutes,
            'volatility': round(volatility * 100, 2)
        }


class MomentumBurstTrader:
    """
    Executes momentum burst trades with 1-5 minute holds.
    """
    
    def __init__(self, initial_capital: float = 100000, max_position_pct: float = 0.05):
        self.capital = initial_capital
        self.max_position_pct = max_position_pct
        self.active_positions: Dict[str, Dict] = {}
        self.trade_history = []
        self.detector = MomentumBurstDetector()
    
    def update_market_data(self, asset: str, price: float, volume: float):
        """Update market data for detector"""
        self.detector.update_price(asset, price, volume)
    
def scan_for_opportunities(self, assets: List[str]) -> List[Dict]:
    """Scan all assets for momentum burst opportunities with probability analysis"""
    opportunities = []
    
    for asset in assets:
        is_burst, direction, confidence, details = self.detector.detect_momentum_burst(asset)
        
        if is_burst and asset not in self.active_positions:
            if asset in self.detector.price_history and self.detector.price_history[asset]:
                current_price = self.detector.price_history[asset][-1]['price']
                
                risk_levels = self.detector.calculate_risk_levels(asset, current_price, direction)
                probability_range = self.detector.calculate_probability_and_range(asset, direction, current_price)
                
                opportunities.append({
                    'asset': asset,
                    'direction': direction,
                    'entry_price': current_price,
                    'confidence': confidence,
                    'stop_loss': risk_levels['stop_loss'],
                    'take_profit_1': risk_levels['take_profit_1'],
                    'take_profit_2': risk_levels['take_profit_2'],
                    'max_hold_minutes': risk_levels['max_hold_minutes'],
                    'volatility': risk_levels['volatility'],
                    'details': details,
                    'probability_analysis': probability_range
                })
    
    opportunities.sort(key=lambda x: x['probability_analysis']['success_probability'], reverse=True)
    return opportunities
    
def execute_trade(self, opportunity: Dict) -> Dict:
    """Execute a momentum burst trade with probability data"""
    asset = opportunity['asset']
    position_size = self.capital * self.max_position_pct / opportunity['entry_price']
    
    trade = {
        'asset': asset,
        'direction': opportunity['direction'],
        'entry_price': opportunity['entry_price'],
        'entry_time': datetime.now(),
        'size': position_size,
        'stop_loss': opportunity['stop_loss'],
        'take_profit_1': opportunity['take_profit_1'],
        'take_profit_2': opportunity['take_profit_2'],
        'max_hold_minutes': opportunity['max_hold_minutes'],
        'confidence': opportunity['confidence'],
        'volatility': opportunity['volatility'],
        'details': opportunity['details'],
        'probability_analysis': opportunity['probability_analysis']
    }
    
    self.active_positions[asset] = trade
    max_position_pct = 0.025
    position_size = (self.capital * max_position_pct) / opportunity['entry_price']
    
    # Ensure position size is reasonable
    position_value = position_size * opportunity['entry_price']
    position_value_pct = (position_value / self.capital) * 100
    
    print(f"📊 Position: {position_size:.2f} units (${position_value:,.2f} = {position_value_pct:.1f}% of capital)")
    
    return trade
def check_positions(self) -> List[Dict]:
        """Check all active positions for exit conditions"""
        closed_trades = []
        
        for asset, trade in list(self.active_positions.items()):
            if asset not in self.detector.price_history or not self.detector.price_history[asset]:
                continue
            
            current_price = self.detector.price_history[asset][-1]['price']
            hold_time = (datetime.now() - trade['entry_time']).total_seconds() / 60
            
            # Check stop loss
            if trade['direction'] == 'BUY':
                stop_hit = current_price <= trade['stop_loss']
                tp1_hit = current_price >= trade['take_profit_1']
                tp2_hit = current_price >= trade['take_profit_2']
            else:
                stop_hit = current_price >= trade['stop_loss']
                tp1_hit = current_price <= trade['take_profit_1']
                tp2_hit = current_price <= trade['take_profit_2']
            
            # Time exit
            time_exit = hold_time >= trade['max_hold_minutes']
            
            if stop_hit or tp2_hit or time_exit:
                # Calculate PnL
                if trade['direction'] == 'BUY':
                    pnl = (current_price - trade['entry_price']) / trade['entry_price']
                else:
                    pnl = (trade['entry_price'] - current_price) / trade['entry_price']
                
                pnl_value = pnl * trade['size'] * trade['entry_price']
                
                closed_trade = {
                    **trade,
                    'exit_price': current_price,
                    'exit_time': datetime.now(),
                    'pnl': pnl_value,
                    'pnl_pct': pnl * 100,
                    'exit_reason': 'stop_loss' if stop_hit else ('take_profit' if tp2_hit else 'timeout'),
                    'hold_minutes': round(hold_time, 1)
                }
                
                self.trade_history.append(closed_trade)
                self.capital += pnl_value
                del self.active_positions[asset]
                closed_trades.append(closed_trade)
        
        return closed_trades
    
def get_performance(self) -> Dict:
        """Get performance metrics for momentum trades"""
        if not self.trade_history:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
        
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        
        return {
            'total_trades': len(self.trade_history),
            'winning_trades': len(winning_trades),
            'win_rate': len(winning_trades) / len(self.trade_history) * 100,
            'total_pnl': total_pnl,
            'avg_hold_minutes': np.mean([t['hold_minutes'] for t in self.trade_history]),
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in self.trade_history if t['pnl'] < 0]) if self.trade_history else 0
        }


class MomentumBurstIntegration:
    """Integrates momentum burst strategy with main system and Telegram"""
    
    def __init__(self):
        self.trader = MomentumBurstTrader()
        self.telegram_bot = None
        self.fast_agents = ['Agent_C', 'Agent_J', 'Agent_D']  # Momentum, Volume, Volatility
        self.assets = ['NAS100/USD', 'XAU/USD', 'BCO/USD', 'S&P500/USD']
    
    def set_telegram_bot(self, bot):
        self.telegram_bot = bot
    
    def update_prices(self, prices: Dict[str, float], volumes: Dict[str, float]):
        """Update prices for all assets"""
        for asset, price in prices.items():
            if asset in self.assets:
                volume = volumes.get(asset, 10000)
                self.trader.update_market_data(asset, price, volume)
    
def scan_and_trade(self) -> List[Dict]:
    """Scan for opportunities and execute trades with detailed alerts"""
    opportunities = self.trader.scan_for_opportunities(self.assets)
    
    executed = []
    for opp in opportunities[:3]:
        trade = self.trader.execute_trade(opp)
        executed.append(trade)
        
        if self.telegram_bot:
            prob = trade['probability_analysis']
            
            # Create visual probability bar
            prob_bar = '█' * int(prob['success_probability'] / 10) + '░' * (10 - int(prob['success_probability'] / 10))
            
            message = f"""
🚀 *MOMENTUM BURST SIGNAL*

📊 *Asset:* {trade['asset']}
🎯 *Action:* {trade['direction']}
📈 *Entry Price:* {trade['entry_price']:.2f}

━━━━━━━━━━━━━━━━━━━━━
*📈 PROBABILITY ANALYSIS*
━━━━━━━━━━━━━━━━━━━━━
🎲 *Success Probability:* {prob['success_probability']:.0f}% {prob_bar}
💪 *Momentum Strength:* {prob['momentum_strength']:.0f}%

━━━━━━━━━━━━━━━━━━━━━
*📊 EXPECTED PRICE RANGE*
━━━━━━━━━━━━━━━━━━━━━
📍 *Expected Range:* {prob['expected_entry_range'][0]:.2f} → {prob['expected_entry_range'][1]:.2f}
📈 *Expected Return:* +{prob['expected_return_pct']:.2f}%
⚖️ *Risk/Reward:* 1:{prob['risk_reward_ratio']:.1f}

━━━━━━━━━━━━━━━━━━━━━
*🎯 CONFIDENCE INTERVALS*
━━━━━━━━━━━━━━━━━━━━━
📊 *68% Confidence:* {prob['confidence_interval_68'][0]:.2f} → {prob['confidence_interval_68'][1]:.2f}
📊 *95% Confidence:* {prob['confidence_interval_95'][0]:.2f} → {prob['confidence_interval_95'][1]:.2f}

━━━━━━━━━━━━━━━━━━━━━
*🛡️ RISK MANAGEMENT*
━━━━━━━━━━━━━━━━━━━━━
🛑 *Stop Loss:* {trade['stop_loss']:.2f}
✅ *TP1:* {trade['take_profit_1']:.2f}
✅ *TP2:* {trade['take_profit_2']:.2f}
⏱️ *Max Hold:* {trade['max_hold_minutes']} minutes

📊 *Volume Ratio:* {trade['details'].get('volume_ratio', 0):.1f}x
⚡ *1-min Return:* {trade['details'].get('return_1min', 0):.2f}%
"""
            self.telegram_bot.send_message(message)
    
    # Check existing positions
    closed = self.trader.check_positions()
    
    for trade in closed:
        if self.telegram_bot:
            emoji = '✅' if trade['pnl'] > 0 else '❌'
            prob = trade.get('probability_analysis', {})
            expected_return = prob.get('expected_return_pct', 0)
            
            message = f"""
{emoji} *MOMENTUM BURST CLOSED*

📊 *Asset:* {trade['asset']}
🎯 *Direction:* {trade['direction']}
📈 *Entry:* {trade['entry_price']:.2f}
📉 *Exit:* {trade['exit_price']:.2f}
💰 *PnL:* ${trade['pnl']:.2f} ({trade['pnl_pct']:.2f}%)
📊 *Vs Expected:* {trade['pnl_pct']:.2f}% / {expected_return:.2f}% expected

⏱️ *Hold Time:* {trade['hold_minutes']} min
📋 *Exit Reason:* {trade['exit_reason']}
"""
            self.telegram_bot.send_message(message)
    
    return executed
def get_status_message(self) -> str:
        """Get formatted status message for Telegram"""
        perf = self.trader.get_performance()
        active = self.trader.active_positions
        
        message = f"""
⚡ *MOMENTUM BURST STRATEGY*

📊 *Performance:*
   • Total Trades: {perf['total_trades']}
   • Win Rate: {perf['win_rate']:.1f}%
   • Total PnL: ${perf['total_pnl']:.2f}
   • Avg Hold: {perf.get('avg_hold_minutes', 0):.1f} min

🎯 *Active Positions:* {len(active)}
"""
        for asset, trade in active.items():
            message += f"\n   • {asset}: {trade['direction']} @ {trade['entry_price']:.2f}"
        
        return message

def calculate_probability_and_range(self, asset: str, direction: str, current_price: float) -> Dict:
    """
    Calculate entry probability, expected price range, and confidence intervals.
    
    Returns:
        Dictionary with:
        - success_probability (0-100%)
        - expected_entry_range (min, max)
        - confidence_interval (68%, 95%)
        - momentum_strength
    """
    if asset not in self.price_history or len(self.price_history[asset]) < 20:
        return {
            'success_probability': 50,
            'expected_entry_range': (current_price * 0.998, current_price * 1.002),
            'confidence_interval_68': (current_price * 0.995, current_price * 1.005),
            'confidence_interval_95': (current_price * 0.99, current_price * 1.01),
            'momentum_strength': 0,
            'risk_reward_ratio': 1.5
        }
    
    # Get recent prices
    prices = [p['price'] for p in list(self.price_history[asset])[-20:]]
    returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
    
    # Calculate statistics
    mean_return = np.mean(returns) if returns else 0
    std_return = np.std(returns) if returns else 0.002
    
    # Current momentum strength (0-100)
    recent_returns = returns[-5:] if len(returns) >= 5 else returns
    momentum_strength = min(100, abs(np.mean(recent_returns)) / 0.003 * 100) if recent_returns else 0
    
    # Success probability based on momentum and volume
    volume_ratio = self.get_volume_ratio(asset)
    base_probability = 50
    
    # Adjust for momentum strength
    if direction == 'BUY' and np.mean(recent_returns) > 0:
        base_probability += momentum_strength * 0.3
    elif direction == 'SELL' and np.mean(recent_returns) < 0:
        base_probability += momentum_strength * 0.3
    else:
        base_probability -= 10
    
    # Adjust for volume
    if volume_ratio > 2.0:
        base_probability += 15
    elif volume_ratio > 1.5:
        base_probability += 8
    
    # Adjust for volatility (lower volatility = higher probability)
    if std_return < 0.002:
        base_probability += 10
    elif std_return > 0.005:
        base_probability -= 10
    
    success_probability = min(95, max(25, base_probability))
    
    # Calculate expected price range
    expected_move = abs(np.mean(recent_returns)) * current_price if recent_returns else current_price * 0.002
    
    if direction == 'BUY':
        expected_min = current_price
        expected_max = current_price + expected_move * 1.5
        range_68_low = current_price - expected_move * 0.5
        range_68_high = current_price + expected_move * 1.2
        range_95_low = current_price - expected_move * 1.0
        range_95_high = current_price + expected_move * 2.0
    else:
        expected_min = current_price - expected_move * 1.5
        expected_max = current_price
        range_68_low = current_price - expected_move * 1.2
        range_68_high = current_price + expected_move * 0.5
        range_95_low = current_price - expected_move * 2.0
        range_95_high = current_price + expected_move * 1.0
    
    # Risk-reward ratio
    stop_distance = abs(current_price - self.calculate_risk_levels(asset, current_price, direction)['stop_loss'])
    take_profit_distance = abs(expected_max - current_price) if direction == 'BUY' else abs(current_price - expected_min)
    risk_reward = take_profit_distance / stop_distance if stop_distance > 0 else 1.5
    
    return {
        'success_probability': round(success_probability, 1),
        'expected_entry_range': (round(expected_min, 4), round(expected_max, 4)),
        'confidence_interval_68': (round(range_68_low, 4), round(range_68_high, 4)),
        'confidence_interval_95': (round(range_95_low, 4), round(range_95_high, 4)),
        'momentum_strength': round(momentum_strength, 1),
        'risk_reward_ratio': round(risk_reward, 2),
        'expected_return_pct': round(expected_move / current_price * 100, 2)
    }
"""
Corrected Momentum Burst Strategy with Monte Carlo Validation
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class CorrectedMomentumStrategy:
    """
    Momentum strategy with proper stop loss calculation and Monte Carlo validation.
    """
    
    def __init__(self):
        self.name = "Momentum Strategy v2"
        self.min_viable_range = 0.002  # Minimum 0.2% profit potential
        self.max_stop_distance = 0.01  # Maximum 1% stop distance
        
    def calculate_viable_levels(self, price: float, direction: str, 
                                  volatility: float, volume_ratio: float) -> Dict:
        """
        Calculate VIABLE stop loss and take profit levels.
        
        For a trade to be viable:
        - Stop loss must be on CORRECT side (below for BUY, above for SELL)
        - Profit potential must be > 2x stop loss distance
        - Expected range must be realistic
        """
        
        # Calculate base movement expectations
        if volume_ratio > 2.0:
            expected_move_pct = volatility * 2.5  # Strong momentum
        elif volume_ratio > 1.5:
            expected_move_pct = volatility * 1.8  # Moderate momentum
        else:
            expected_move_pct = volatility * 1.2  # Weak momentum
        
        # Stop loss distance (1.5x volatility, but on correct side)
        stop_distance_pct = volatility * 1.5
        stop_distance = price * stop_distance_pct
        
        # Take profit distance (2x stop distance minimum)
        tp_distance_pct = max(stop_distance_pct * 2, expected_move_pct)
        tp_distance = price * tp_distance_pct
        
        if direction == 'BUY':
            # ✅ CORRECT: Stop BELOW entry
            stop_loss = price - stop_distance
            take_profit = price + tp_distance
        else:
            # ✅ CORRECT: Stop ABOVE entry
            stop_loss = price + stop_distance
            take_profit = price - tp_distance
        
        # Validate stop loss is on correct side
        is_valid = False
        validation_message = ""
        
        if direction == 'BUY':
            if stop_loss < price:
                is_valid = True
                validation_message = f"Stop loss ${stop_loss:.2f} correctly below entry ${price:.2f}"
            else:
                is_valid = False
                validation_message = f"❌ ERROR: Stop loss ${stop_loss:.2f} is ABOVE entry ${price:.2f}"
        else:  # SELL
            if stop_loss > price:
                is_valid = True
                validation_message = f"Stop loss ${stop_loss:.2f} correctly above entry ${price:.2f}"
            else:
                is_valid = False
                validation_message = f"❌ ERROR: Stop loss ${stop_loss:.2f} is BELOW entry ${price:.2f}"
        
        # Calculate risk-reward ratio
        if direction == 'BUY':
            risk = price - stop_loss
            reward = take_profit - price
        else:
            risk = stop_loss - price
            reward = price - take_profit
        
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'stop_distance_pct': round(stop_distance_pct * 100, 2),
            'expected_move_pct': round(expected_move_pct * 100, 2),
            'risk_reward_ratio': round(risk_reward, 2),
            'is_valid': is_valid,
            'validation_message': validation_message,
            'viable': is_valid and risk_reward >= 1.5
        }
    
    def monte_carlo_validation(self, current_price: float, direction: str,
                                volatility: float, volume_ratio: float,
                                n_simulations: int = 1000) -> Dict:
        """
        Monte Carlo simulation to validate trade viability.
        
        Returns:
            - Win probability
            - Expected profit
            - Probability of stop loss hit
            - Probability of take profit hit
        """
        np.random.seed(42)
        
        # Parameters based on volume spike
        if volume_ratio > 2.0:
            drift = 0.002 if direction == 'BUY' else -0.002  # Strong drift
        elif volume_ratio > 1.5:
            drift = 0.001 if direction == 'BUY' else -0.001  # Moderate drift
        else:
            drift = 0.0005 if direction == 'BUY' else -0.0005  # Weak drift
        
        # Simulate price paths for 8 minutes (8 steps of 1 minute)
        dt = 1
        n_steps = 8
        paths = np.zeros((n_simulations, n_steps + 1))
        paths[:, 0] = current_price
        
        for t in range(1, n_steps + 1):
            shock = np.random.normal(drift, volatility, n_simulations)
            paths[:, t] = paths[:, t-1] * (1 + shock)
        
        final_prices = paths[:, -1]
        
        # Calculate target levels
        if direction == 'BUY':
            stop_level = current_price * (1 - volatility * 1.5)
            tp_level = current_price * (1 + volatility * 2.5)
        else:
            stop_level = current_price * (1 + volatility * 1.5)
            tp_level = current_price * (1 - volatility * 2.5)
        
        # Calculate probabilities
        if direction == 'BUY':
            win_prob = np.sum(final_prices > current_price) / n_simulations * 100
            stop_hit_prob = np.sum(final_prices < stop_level) / n_simulations * 100
            tp_hit_prob = np.sum(final_prices > tp_level) / n_simulations * 100
        else:
            win_prob = np.sum(final_prices < current_price) / n_simulations * 100
            stop_hit_prob = np.sum(final_prices > stop_level) / n_simulations * 100
            tp_hit_prob = np.sum(final_prices < tp_level) / n_simulations * 100
        
        expected_return = (np.mean(final_prices) - current_price) / current_price * 100
        
        return {
            'win_probability': round(win_prob, 1),
            'stop_hit_probability': round(stop_hit_prob, 1),
            'tp_hit_probability': round(tp_hit_prob, 1),
            'expected_return_pct': round(expected_return, 2),
            'is_viable': win_prob > 55 and stop_hit_prob < 40,
            'recommendation': 'TRADE' if (win_prob > 55 and stop_hit_prob < 40) else 'AVOID'
        }
    
    def detect_momentum_burst(self, price: float, volume_ratio: float,
                               price_change_pct: float) -> Tuple[bool, str, float]:
        """
        Detect genuine momentum burst.
        
        Returns:
            (is_burst, direction, strength)
        """
        is_burst = False
        direction = 'NEUTRAL'
        strength = 0
        
        # Check if price is moving with volume
        if abs(price_change_pct) > 0.002 and volume_ratio > 1.5:
            is_burst = True
            direction = 'BUY' if price_change_pct > 0 else 'SELL'
            strength = min(100, (abs(price_change_pct) / 0.003 * 100) + (volume_ratio / 2 * 10))
        
        return is_burst, direction, strength
    
    def analyze_trade(self, price: float, direction: str, 
                       volatility: float, volume_ratio: float,
                       price_change_pct: float) -> Dict:
        """
        Complete trade analysis with validation.
        """
        # Step 1: Calculate viable levels
        levels = self.calculate_viable_levels(price, direction, volatility, volume_ratio)
        
        # Step 2: Run Monte Carlo simulation
        monte_carlo = self.monte_carlo_validation(price, direction, volatility, volume_ratio)
        
        # Step 3: Final decision
        can_trade = levels['viable'] and monte_carlo['is_viable']
        
        if not levels['viable']:
            reason = levels['validation_message']
        elif not monte_carlo['is_viable']:
            reason = f"Monte Carlo: win prob {monte_carlo['win_probability']:.0f}%, stop hit {monte_carlo['stop_hit_probability']:.0f}%"
        else:
            reason = "All validation passed"
        
        return {
            'can_trade': can_trade,
            'direction': direction,
            'entry_price': price,
            'stop_loss': levels['stop_loss'],
            'take_profit': levels['take_profit'],
            'risk_reward': levels['risk_reward_ratio'],
            'expected_move_pct': levels['expected_move_pct'],
            'monte_carlo': monte_carlo,
            'reason': reason,
            'levels_valid': levels['is_valid'],
            'volume_ratio': volume_ratio,
            'price_change_pct': price_change_pct
        }
# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("MOMENTUM BURST STRATEGY - TEST")
    print("=" * 60)
    
    # Initialize
    momentum = MomentumBurstIntegration()
    
    # Simulate price updates
    print("\n📊 Simulating market data...")
    
    import random
    np.random.seed(42)
    
    for i in range(100):
        # Simulate NASDAQ price with momentum bursts
        if i < 50:
            price = 18000 + np.random.normal(0, 50)
            volume = 10000 + np.random.normal(0, 1000)
        else:
            # Create a momentum burst
            price = 18100 + (i - 50) * 10
            volume = 25000 + np.random.normal(0, 2000)
        
        prices = {'NAS100/USD': price}
        volumes = {'NAS100/USD': volume}
        
        momentum.update_prices(prices, volumes)
        
        if i % 20 == 0:
            trades = momentum.scan_and_trade()
            if trades:
                print(f"\n📊 Trade executed at step {i}")
    
    print("\n" + "=" * 60)
    print(momentum.get_status_message())
    print("=" * 60)
    
    print("\n✅ Momentum burst strategy ready")
