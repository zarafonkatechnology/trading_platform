# C:\trading_platform\forex_engine\brokers\eurusd_broker.py

import logging
import numpy as np
import random
from datetime import datetime
from typing import Dict, List, Optional

# Use absolute import from the brokers package
try:
    from brokers.base_broker import BaseBroker
except ImportError:
    # Fallback for direct execution
    from base_broker import BaseBroker

logger = logging.getLogger(__name__)

class AUDUSDBroker(BaseBroker):
    """
    AUD/USD Broker - Commodity Currency.
    Strategy: Gold correlation + risk sentiment.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="AUDUSD",
            config=config
        )
        
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 1.0
        self.max_position_size = 4
        self.gear_type = 'INVERSE'
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        self.pattern_info = None
        self.squeeze_detected = False
        self.volume_spike = False
        self.support_level = 0.0
        self.resistance_level = 0.0
        self.name = "AUDUSD_Broker"
        self.agent_type = "Gold correlation + risk sentiment"
        self.specialization = "Adaptive Moving Average"
        
        # ===== ADD MISSING ATTRIBUTES =====
        self.rba_policy = config.get('rba_policy', 'NEUTRAL')
        self.rba_rate = config.get('rba_rate', 4.35)
        self.china_pmi = config.get('china_pmi', 50.0)
        self.is_blocked = False
        self.position_multiplier = 1.0
        
        # Gold tracking
        self.gold_price = 0.0
        self.gold_change_pct = 0.0
        
        # Risk sentiment
        self.risk_sentiment = 0.0
        self.vix = 15.0
        
        # AUD-specific external data
        self.iron_ore_price = 0.0
        self.copper_price = 0.0
        
        # State
        self.signal = 'HOLD'
        self.confidence = 50.0
        self.z_score = 0.0
        
        logger.info(f"✅ AUDUSD Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")

    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        self.gold_price = market_data.get('GOLD', 0)
        self.gold_change_pct = market_data.get('gold_change_pct', 0)
        risk_sentiment = market_data.get('risk_sentiment', 0.0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'AUDUSD: '
        
        if abs(self.gold_change_pct) > 0.5:
            if self.gold_change_pct > 0:
                confidence_boost = 15
                bias = 'BUY'
                reasoning += f'Gold up {self.gold_change_pct:.1f}% → AUD strength → BUY'
            else:
                confidence_boost = 15
                bias = 'SELL'
                reasoning += f'Gold down {self.gold_change_pct:.1f}% → AUD weakness → SELL'
        else:
            reasoning += f'Neutral gold ({self.gold_price:.2f})'
        
        if risk_sentiment > 0.5:
            reasoning += ', risk-on → AUD strength'
            if bias == 'NEUTRAL':
                bias = 'BUY'
                confidence_boost = 10
        elif risk_sentiment < -0.5:
            reasoning += ', risk-off → AUD weakness'
            if bias == 'NEUTRAL':
                bias = 'SELL'
                confidence_boost = 10
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'gold_price': self.gold_price,
            'gold_change_pct': self.gold_change_pct,
            'risk_sentiment': risk_sentiment
        }
    
    def _get_pair_confidence_boost(self) -> float:
        if abs(self.gold_change_pct) > 1.0:
            return 15.0
        return 5.0
    def analyze(self, signal_data: Dict) -> Dict:
        """AUDUSD analysis using base class with AUD-specific logic."""
        try:
              # ===== STEP 1: Get base analysis from parent =====
              base_result = super().analyze(signal_data)
              
              # ===== STEP 2: Get AUDUSD-specific data =====
              current_price = signal_data.get('price', signal_data.get('current_price', 0))
              candles = signal_data.get('candles', [])
              
              if not candles:
                      return base_result
              
              closes = [c['close'] for c in candles]
              highs = [c['high'] for c in candles]
              lows = [c['low'] for c in candles]
              
              if len(closes) < 20:
                      return base_result
              
              # Update histories
              self.close_history.extend(closes)
              self.high_history.extend(highs)
              self.low_history.extend(lows)
              
              # ===== STEP 3: Get AUDUSD external data =====
              # Gold (AUD is commodity currency)
              self.gold_price = signal_data.get('GOLD', 0)
              self.gold_change_pct = signal_data.get('gold_change_pct', 0)
              
              # RBA Policy (Reserve Bank of Australia)
              self.rba_policy = signal_data.get('rba_policy', 'NEUTRAL')
              self.rba_rate = signal_data.get('rba_rate', 4.35)
              
              # China PMI (China is Australia's largest trading partner)
              self.china_pmi = signal_data.get('china_pmi', 50.0)
              
              # Risk Sentiment
              self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
              self.vix = signal_data.get('VIX', 15.0)
              
              # ===== STEP 4: Detect candlestick patterns =====
              candle_pattern = self._detect_candlestick_pattern(closes, highs, lows)
              if candle_pattern:
                      self.pattern_info = candle_pattern
              
              # ===== STEP 5: Check event blocks =====
              events = self._get_upcoming_events()
              event_check = self._check_event_block(events)
              self.is_blocked = event_check['is_blocked']
              
              if self.is_blocked:
                      base_result['vote'] = 'HOLD'
                      base_result['confidence'] = 30
                      base_result['reasoning'] = f"BLOCKED: {event_check.get('reason', 'High impact event')}"
                      return base_result
              
              # ===== STEP 6: Generate AUDUSD signal =====
              aud_result = self._generate_audusd_signal(current_price, candle_pattern)
              
              # ===== STEP 7: Apply gold correlation adjustment =====
              aud_result = self._adjust_for_gold_correlation(aud_result)
              
              # ===== STEP 8: Override base if needed =====
              base_signal = base_result.get('vote', 'HOLD')
              base_conf = base_result.get('confidence', 0)
              
              if base_signal == 'HOLD' and aud_result['vote'] != 'HOLD' and aud_result['confidence'] >= 60:
                      # Override with AUD signal
                      base_result['vote'] = aud_result['vote']
                      base_result['confidence'] = aud_result['confidence']
                      base_result['reasoning'] = f"{aud_result['reasoning']} (AUDUSD override)"
                      base_result['z_score'] = self.z_score
              elif base_signal != 'HOLD' and aud_result['vote'] != 'HOLD':
                      # Both have signals - use the stronger one
                      if aud_result['confidence'] > base_conf + 10:
                            base_result['vote'] = aud_result['vote']
                            base_result['confidence'] = aud_result['confidence']
                            base_result['reasoning'] = f"{aud_result['reasoning']} (stronger than base)"
              
              # ===== STEP 9: Add AUDUSD-specific data =====
              base_result['gold_price'] = self.gold_price
              base_result['gold_change_pct'] = self.gold_change_pct
              base_result['rba_policy'] = self.rba_policy
              base_result['rba_rate'] = self.rba_rate
              base_result['china_pmi'] = self.china_pmi
              base_result['risk_sentiment'] = self.risk_sentiment
              base_result['vix'] = self.vix
              base_result['pattern_info'] = self.pattern_info
              
              return base_result
              
        except Exception as e:
              logger.error(f"AUDUSD Broker error: {e}")
              import traceback
              traceback.print_exc()
              return self._hold_response(f"Error: {str(e)}")
    def monte_carlo(self, current_price: float, direction: str, 
                gold_volatility: float = 0.01) -> Dict:
        """
        Monte Carlo with commodity correlation.
        """
        n_sims = 5000
        horizon = 20
        wins = 0
        
        # Gold correlation factor
        gold_factor = 1.0 + abs(self.gold_change_pct) / 100
        
        for _ in range(n_sims):
               price = current_price
               for _ in range(horizon):
                     # Higher volatility when gold is moving
                     vol = 0.005 * gold_factor
                     shock = np.random.normal(0, vol)
                     # Mean reversion to RBA rate expectation
                     price *= (1 + shock)
               
               if direction == 'BUY' and price > current_price:
                     wins += 1
               elif direction == 'SELL' and price < current_price:
                     wins += 1
        
        confidence = wins / n_sims * 100
        return {'entry_confidence': min(95, confidence)}
    def _calculate_reward(self, trade_result, agent_votes):
        pnl = trade_result.get('pnl', 0)
        
        # Penalty for agent disagreement
        consensus = sum(1 for v in agent_votes if v == 'BUY') / len(agent_votes)
        confusion_penalty = abs(consensus - 0.5) * 10  # Max 5% penalty
        
        # Bonus for strong agent agreement
        agreement_bonus = consensus * 5
        
        return pnl / 100 - confusion_penalty + agreement_bonus
    def _detect_candlestick_pattern(self, closes: List[float], highs: List[float], 
                                   lows: List[float]) -> Optional[Dict]:
        """
        Detect candlestick patterns for AUDUSD.
        """
        if len(closes) < 3:
            return None
        
        # Get last 3 candles
        c1, c2, c3 = closes[-3], closes[-2], closes[-1]
        h1, h2, h3 = highs[-3], highs[-2], highs[-1]
        l1, l2, l3 = lows[-3], lows[-2], lows[-1]
        
        # Calculate candle bodies and shadows
        body1 = abs(c1 - closes[-4]) if len(closes) >= 4 else abs(c1 - c2)
        body2 = abs(c2 - c1)
        body3 = abs(c3 - c2)
        
        upper_shadow3 = h3 - max(c3, c2)
        lower_shadow3 = min(c3, c2) - l3
        
        # ===== DOJI (Indecision) =====
        if body3 < 0.0002:  # Very small body
            return {
                'pattern': 'Doji',
                'direction': 'NEUTRAL',
                'confidence': 60,
                'message': 'Doji detected - market indecision'
            }
        
        # ===== ENGULFING PATTERN =====
        # Bullish Engulfing: Green candle engulfs previous red candle
        if c3 > c2 and c2 < c1 and c3 > c1 and c2 > c1:
            return {
                'pattern': 'Bullish Engulfing',
                'direction': 'BUY',
                'confidence': 80,
                'message': 'Bullish engulfing pattern - strong reversal signal'
            }
        
        # Bearish Engulfing: Red candle engulfs previous green candle
        if c3 < c2 and c2 > c1 and c3 < c1 and c2 < c1:
            return {
                'pattern': 'Bearish Engulfing',
                'direction': 'SELL',
                'confidence': 80,
                'message': 'Bearish engulfing pattern - strong reversal signal'
            }
        
        # ===== HAMMER / SHOOTING STAR =====
        # Hammer (Bullish): Small body, long lower shadow, little upper shadow
        if body3 < 0.0003 and lower_shadow3 > body3 * 2 and upper_shadow3 < body3 * 0.5:
            return {
                'pattern': 'Hammer',
                'direction': 'BUY',
                'confidence': 70,
                'message': 'Hammer pattern - potential bullish reversal'
            }
        
        # Shooting Star (Bearish): Small body, long upper shadow, little lower shadow
        if body3 < 0.0003 and upper_shadow3 > body3 * 2 and lower_shadow3 < body3 * 0.5:
            return {
                'pattern': 'Shooting Star',
                'direction': 'SELL',
                'confidence': 70,
                'message': 'Shooting star pattern - potential bearish reversal'
            }
        
        # ===== THREE WHITE SOLDIERS / THREE BLACK CROWS =====
        # Three White Soldiers: Three consecutive green candles with higher closes
        if c3 > c2 > c1 and c3 > c2 > c1 and all(c > c_prev for c, c_prev in [(c2, c1), (c3, c2)]):
            return {
                'pattern': 'Three White Soldiers',
                'direction': 'BUY',
                'confidence': 75,
                'message': 'Three white soldiers - strong bullish momentum'
            }
        
        # Three Black Crows: Three consecutive red candles with lower closes
        if c3 < c2 < c1 and c3 < c2 < c1 and all(c < c_prev for c, c_prev in [(c2, c1), (c3, c2)]):
            return {
                'pattern': 'Three Black Crows',
                'direction': 'SELL',
                'confidence': 75,
                'message': 'Three black crows - strong bearish momentum'
            }
        
        return None
    
    def _adjust_for_gold_correlation(self, result: Dict) -> Dict:
        """
        Adjust signal based on gold price correlation.
        AUDUSD moves with Gold prices.
        """
        if abs(self.gold_change_pct) > 0.3:
            if self.gold_change_pct > 0:  # Gold up → AUD strength
                if result['vote'] == 'BUY':
                    result['confidence'] = min(95, result['confidence'] + 15)
                    result['reasoning'] += " | Gold up confirms BUY"
                elif result['vote'] == 'SELL':
                    result['confidence'] = max(40, result['confidence'] - 15)
                    result['reasoning'] += " | Gold up contradicts SELL"
                    if result['confidence'] < 50:
                        result['vote'] = 'HOLD'
                        result['reasoning'] = "Gold correlation overrides signal"
            else:  # Gold down → AUD weakness
                if result['vote'] == 'SELL':
                    result['confidence'] = min(95, result['confidence'] + 15)
                    result['reasoning'] += " | Gold down confirms SELL"
                elif result['vote'] == 'BUY':
                    result['confidence'] = max(40, result['confidence'] - 15)
                    result['reasoning'] += " | Gold down contradicts BUY"
                    if result['confidence'] < 50:
                        result['vote'] = 'HOLD'
                        result['reasoning'] = "Gold correlation overrides signal"
        
        return result
    
    def _generate_audusd_signal(self, current_price: float, candle_pattern: Optional[Dict]) -> Dict:
        """
        Generate AUDUSD-specific signal with gold and China data.
        """
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== RBA POLICY =====
        if self.rba_policy == 'HAWKISH':
            if self.gold_change_pct > 0:
                action = 'BUY'
                confidence = 80
                reasoning = ["RBA hawkish + Gold rising → AUD strength"]
            elif self.gold_change_pct < -0.5:
                action = 'HOLD'
                confidence = 40
                reasoning = ["RBA hawkish but Gold falling → mixed signals"]
        
        elif self.rba_policy == 'DOVISH':
            if self.gold_change_pct < 0:
                action = 'SELL'
                confidence = 80
                reasoning = ["RBA dovish + Gold falling → AUD weakness"]
            elif self.gold_change_pct > 0.5:
                action = 'HOLD'
                confidence = 40
                reasoning = ["RBA dovish but Gold rising → mixed signals"]
        
        # ===== CHINA ECONOMIC DATA =====
        if self.china_pmi > 52:
            reasoning.append(f"China PMI strong ({self.china_pmi:.1f}) → AUD demand")
            if action == 'BUY':
                confidence = min(95, confidence + 10)
            elif action == 'HOLD':
                action = 'BUY'
                confidence = 65
                reasoning.append("China PMI strong → BUY AUD")
        
        elif self.china_pmi < 48:
            reasoning.append(f"China PMI weak ({self.china_pmi:.1f}) → AUD weakness")
            if action == 'SELL':
                confidence = min(95, confidence + 10)
            elif action == 'HOLD':
                action = 'SELL'
                confidence = 65
                reasoning.append("China PMI weak → SELL AUD")
        
        # ===== CANDLESTICK CONFIRMATION =====
        if candle_pattern and candle_pattern['confidence'] > 70:
            if action == 'HOLD':
                action = candle_pattern['direction']
                confidence = candle_pattern['confidence']
                reasoning.append(f"Candlestick: {candle_pattern['pattern']}")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
            reasoning = ["AUDUSD: No clear signal from RBA, Gold, or China data"]
        
        return {
            'vote': action,
            'confidence': confidence,
            'reasoning': '; '.join(reasoning) if reasoning else 'AUDUSD economic analysis'
        }
    
    def _get_upcoming_events(self) -> List[Dict]:
        """Get upcoming economic events for AUDUSD."""
        events = []
        current_hour = datetime.now().hour
        
        # RBA decisions (usually first Tuesday of month)
        if datetime.now().weekday() == 1 and datetime.now().day <= 7:
            if 9 <= current_hour <= 12:  # RBA decision time (Sydney time)
                events.append({
                    'name': 'RBA Rate Decision',
                    'impact': 'HIGH',
                    'time_minutes': random.randint(5, 30),
                    'description': 'Interest rate decision'
                })
        
        # China PMI (end of month)
        if datetime.now().day >= 28:
            events.append({
                'name': 'China PMI Release',
                'impact': 'HIGH',
                'time_minutes': random.randint(10, 40),
                'description': 'Manufacturing PMI'
            })
        
        # AU CPI (quarterly)
        if datetime.now().month in [1, 4, 7, 10] and datetime.now().day <= 10:
            events.append({
                'name': 'Australia CPI',
                'impact': 'HIGH',
                'time_minutes': random.randint(10, 30),
                'description': 'Consumer Price Index'
            })
        
        return events
    
    def _check_event_block(self, events: List[Dict]) -> Dict:
        """Check if events are blocking trading."""
        for event in events:
            if event['impact'] == 'HIGH' and event['time_minutes'] < 60:
                return {
                    'is_blocked': True,
                    'reason': f"{event['name']} in {event['time_minutes']} minutes - NO TRADING ALLOWED",
                    'has_medium_impact': False
                }
        
        for event in events:
            if event['impact'] == 'MEDIUM' and event['time_minutes'] < 45:
                return {
                    'is_blocked': False,
                    'has_medium_impact': True,
                    'medium_reason': f"{event['name']} in {event['time_minutes']} minutes"
                }
        
        return {
            'is_blocked': False,
            'has_medium_impact': False
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                            n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Simulate future price paths and predict cloud position probability.
        """
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        
        for _ in range(n_sims):
            price = current_price
            path = [price]
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
                path.append(price)
            
            final_price = path[-1]
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if final_price > cloud_top:
                outcomes['above_cloud'] += 1
            elif final_price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        
        probabilities = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probabilities['above_cloud'] > 60:
            vote = 'BUY'
            confidence = probabilities['above_cloud']
        elif probabilities['below_cloud'] > 60:
            vote = 'SELL'
            confidence = probabilities['below_cloud']
        else:
            vote = 'HOLD'
            confidence = probabilities['inside_cloud']
        
        return {'vote': vote, 'confidence': confidence, 'probabilities': probabilities}
    
    def predict(self, signal_data: Dict, market_features: Dict = None) -> tuple:
        """Original predict method for compatibility with agent system."""
        result = self.analyze(signal_data)
        return result['vote'], result['confidence']
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'name': self.name,
            'pair': self.pair,
            'agent_type': self.agent_type,
            'specialization': self.specialization,
            'signal': self.signal,
            'confidence': self.confidence,
            'z_score': self.z_score,
            'gold_price': self.gold_price,
            'gold_change_pct': self.gold_change_pct,
            'rba_policy': self.rba_policy,
            'rba_rate': self.rba_rate,
            'china_pmi': self.china_pmi,
            'is_blocked': self.is_blocked,
            'position_multiplier': self.position_multiplier,
            'timestamp': datetime.now().isoformat()
        }