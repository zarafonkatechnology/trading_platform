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

class USDCHFBroker(BaseBroker):
    """
    USD/CHF Broker - Safe Haven.
    Strategy: VIX + safe haven flows.
    """
    
    def __init__(self, config: Dict = None):
        if config is None:
            config = {}
        
        super().__init__(
            pair="USDCHF",
            config=config
        )
        
        self.entry_threshold = config.get('entry_threshold', 1.8)
        self.exit_threshold = config.get('exit_threshold', 0.3)
        self.sl_pips = config.get('sl_pips', 12)
        self.tp_pips = config.get('tp_pips', 25)
        self.volume_multiplier = 0.8
        self.max_position_size = 3
        self.gear_type = 'DIRECT'
        self.snb_intervention_history = []
        self.close_history = []
        self.high_history = []
        self.low_history = []
        self.volume_history = []
        self.pattern_info = None
        self.squeeze_detected = False
        self.volume_spike = False
        self.support_level = 0.0
        self.resistance_level = 0.0
        self.name = "USDCHF_Broker"
        self.agent_type = "Safe Haven"
        self.specialization = "Head & Shoulders + Double Top/Bottom"
        # Safe haven indicators
        self.vix = 0.0
        self.safe_haven_flow = 0.0
        
        logger.info(f"✅ USDCHF Broker initialized")
        logger.info(f"   Entry: {self.entry_threshold} | Exit: {self.exit_threshold}")
        logger.info(f"   SL: {self.sl_pips}pips | TP: {self.tp_pips}pips")
    
    def _apply_pair_specific_logic(self, market_data: Dict) -> Dict:
        self.vix = market_data.get('VIX', 15.0)
        self.safe_haven_flow = market_data.get('safe_haven_flow', 0.0)
        
        confidence_boost = 0
        bias = 'NEUTRAL'
        reasoning = 'USDCHF: '
        
        # VIX spike = risk-off = CHF strength
        if self.vix > 25:
            confidence_boost = 15
            bias = 'SELL'  # CHF strength → USDCHF down
            reasoning += f'VIX spike ({self.vix:.1f}) → CHF strength → SELL'
        elif self.vix < 15:
            reasoning += f'Low VIX ({self.vix:.1f}) → risk-on'
            if self.z_score < -1.5:
                bias = 'BUY'
                confidence_boost = 10
                reasoning += ' → oversold → BUY'
        else:
            reasoning += f'Neutral VIX ({self.vix:.1f})'
        
        # Safe haven flow
        if abs(self.safe_haven_flow) > 0.5:
            if self.safe_haven_flow > 0:
                reasoning += ', safe haven flow into CHF → SELL'
                if bias == 'NEUTRAL':
                    bias = 'SELL'
                    confidence_boost = 15
            else:
                reasoning += ', safe haven flow out of CHF → BUY'
                if bias == 'NEUTRAL':
                    bias = 'BUY'
                    confidence_boost = 15
        
        return {
            'bias': bias,
            'confidence_boost': confidence_boost,
            'reasoning': reasoning,
            'vix': self.vix,
            'safe_haven_flow': self.safe_haven_flow
        }
    
    def _get_pair_confidence_boost(self) -> float:
        if self.vix > 25:
            return 15.0
        return 5.0

    def analyze(self, signal_data: Dict) -> Dict:
        """
        USDCHF-specific analysis with Safe Haven and Sentiment.
        """
        try:
            current_price = signal_data.get('price', signal_data.get('current_price', 0))
            candles = signal_data.get('candles', [])
            
            if not candles:
                logger.info("📉 USDCHF: no candle data, using price-based fallback")
                closes = [current_price]
                highs = [current_price]
                lows = [current_price]
            else:
                closes = [c['close'] for c in candles]
                highs = [c['high'] for c in candles]
                lows = [c['low'] for c in candles]
            
            # Update history
            self.close_history.extend(closes)
            self.high_history.extend(highs)
            self.low_history.extend(lows)
            self.price_history.append(current_price)
            
            # ===== GET EXTERNAL DATA =====
            self.vix = signal_data.get('VIX', 15.0)
            self.risk_sentiment = signal_data.get('risk_sentiment', 0.0)
            self.geopolitical_risk = signal_data.get('geopolitical_risk', 0.0)
            self.safe_haven_flow = signal_data.get('safe_haven_flow', 0.0)
            self.snb_policy = signal_data.get('snb_policy', 'NEUTRAL')
            self.snb_intervention_level = signal_data.get('snb_intervention_level', 0.0)
            
            # ===== SAFE HAVEN ANALYSIS =====
            safe_haven_result = self._analyze_safe_haven(current_price)
            
            # ===== SENTIMENT ANALYSIS =====
            sentiment_result = self._analyze_sentiment(signal_data)
            
            # ===== STOP HUNT & SPOOFING DETECTION =====
            stop_hunt = self._detect_stop_hunt(current_price, signal_data.get('volume', 1000))
            spoofing = self._detect_spoofing(signal_data)
            distribution = self._detect_distribution(current_price, signal_data.get('volume', 1000))
            
            # ===== SNB INTERVENTION DETECTION =====
            snb_intervention = self._detect_snb_intervention(current_price, signal_data)
            
            # ===== GENERATE SIGNAL =====
            result = self._generate_usdchf_signal(
                current_price,
                safe_haven_result,
                sentiment_result,
                stop_hunt,
                spoofing,
                distribution,
                snb_intervention
            )
            
            # ===== UPDATE STATE =====
            self.signal = result['vote']
            self.confidence = result['confidence']
            self.stop_hunt_detected = stop_hunt['detected']
            self.stop_hunt_direction = stop_hunt['direction']
            self.spoofing_detected = spoofing['detected']
            self.spoofing_direction = spoofing['direction']
            self.distribution_detected = distribution['detected']
            self.distribution_direction = distribution['direction']
            
            # Calculate Z-score for exit
            if len(closes) > 1:
                window = closes[-20:] if len(closes) >= 20 else closes
                mu = np.mean(window)
                sigma = np.std(window)
                self.z_score = (current_price - mu) / sigma if sigma > 0 else 0
            
            # Log decision
            logger.info(f"{self.name}: {result['vote']} on USDCHF ({result['confidence']:.0f}%)")
            logger.info(f"   Safe Haven Flow: {self.safe_haven_flow:.2f}")
            logger.info(f"   VIX: {self.vix:.1f}")
            logger.info(f"   SNB Intervention: {snb_intervention}")
            logger.info(f"   Stop Hunt: {stop_hunt['detected']}")
            logger.info(f"   Reasoning: {result['reasoning']}")
            
            return {
                'pair': self.pair,
                'vote': result['vote'],
                'confidence': round(min(95, result['confidence']), 1),
                'reasoning': result['reasoning'],
                'z_score': self.z_score,
                'stop_hunt': stop_hunt,
                'spoofing': spoofing,
                'distribution': distribution,
                'safe_haven_flow': self.safe_haven_flow,
                'vix': self.vix,
                'risk_sentiment': self.risk_sentiment,
                'sentiment_data': sentiment_result,
                'snb_intervention': snb_intervention,
                'snb_policy': self.snb_policy,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _analyze_safe_haven(self, current_price: float) -> Dict:
        """
        Analyze safe haven flows for USDCHF.
        """
        # Safe haven flow calculation
        safe_haven_score = 50
        
        # VIX effect (high VIX = safe haven demand)
        if self.vix > 25:
            safe_haven_score += 20  # CHF strength
            logger.info(f"🛡️ High VIX ({self.vix:.1f}) - safe haven demand for CHF")
        elif self.vix < 15:
            safe_haven_score -= 15  # CHF weakness (risk-on)
            logger.info(f"🌍 Low VIX ({self.vix:.1f}) - risk-on, CHF weakness")
        
        # Geopolitical risk
        if self.geopolitical_risk > 0.5:
            safe_haven_score += 15
            logger.info(f"🛡️ Geopolitical risk elevated - safe haven demand")
        elif self.geopolitical_risk < -0.3:
            safe_haven_score -= 10
        
        # Safe haven flow (direct measure)
        if self.safe_haven_flow > 0.3:
            safe_haven_score += 15
            logger.info(f"🛡️ Safe haven flow into CHF")
        elif self.safe_haven_flow < -0.3:
            safe_haven_score -= 15
            logger.info(f"🌍 Safe haven flow out of CHF")
        
        # SNB intervention (if SNB is selling CHF, it's bearish for CHF)
        if self.snb_intervention_level > 0.5:
            safe_haven_score -= 20
            logger.info(f"🏦 SNB intervention detected - selling CHF")
        
        # Determine direction
        if safe_haven_score > 65:
            direction = 'SELL'  # CHF strength → USDCHF down
            confidence = min(90, 60 + (safe_haven_score - 65))
        elif safe_haven_score < 35:
            direction = 'BUY'   # CHF weakness → USDCHF up
            confidence = min(90, 60 + (35 - safe_haven_score))
        else:
            direction = 'NEUTRAL'
            confidence = 50
        
        return {
            'score': safe_haven_score,
            'direction': direction,
            'confidence': confidence,
            'message': f"Safe haven score: {safe_haven_score:.0f}"
        }
    
    def _analyze_sentiment(self, signal_data: Dict) -> Dict:
        """
        Analyze sentiment for USDCHF.
        """
        # Get sentiment from signal data or calculate
        self.bullish_sentiment = signal_data.get('bullish_sentiment', 0.4)
        self.bearish_sentiment = signal_data.get('bearish_sentiment', 0.3)
        self.neutral_sentiment = 1.0 - self.bullish_sentiment - self.bearish_sentiment
        
        # Detect sentiment extreme
        if self.bullish_sentiment > 0.75:
            self.sentiment_extreme = True
            sentiment_direction = 'BEARISH'  # Contrarian: extreme bullish = sell
            confidence = 80
            message = "Extreme bullish sentiment - contrarian SELL signal"
        elif self.bearish_sentiment > 0.75:
            self.sentiment_extreme = True
            sentiment_direction = 'BULLISH'  # Contrarian: extreme bearish = buy
            confidence = 80
            message = "Extreme bearish sentiment - contrarian BUY signal"
        else:
            self.sentiment_extreme = False
            sentiment_direction = 'NEUTRAL'
            confidence = 50
            message = "Normal sentiment levels"
        
        return {
            'bullish': self.bullish_sentiment,
            'bearish': self.bearish_sentiment,
            'neutral': self.neutral_sentiment,
            'extreme': self.sentiment_extreme,
            'direction': sentiment_direction,
            'confidence': confidence,
            'message': message
        }
    
    def _detect_stop_hunt(self, current_price: float, volume: float) -> Dict:
        """
        Detect stop hunts in USDCHF.
        USDCHF is known for stop hunts due to low liquidity.
        """
        if len(self.price_history) < 10:
            return {'detected': False, 'direction': 'HOLD', 'reason': ''}
        
        # Calculate recent price range
        recent_prices = list(self.price_history)[-20:]
        recent_high = max(recent_prices)
        recent_low = min(recent_prices)
        
        # Check for spike above resistance or below support
        if current_price > recent_high * 1.002:
            # Price spiked above resistance
            # Check if it immediately reversed (stop hunt)
            if len(self.price_history) >= 3:
                prev_price = list(self.price_history)[-2]
                if current_price > prev_price and prev_price < recent_high:
                    # This is a stop hunt
                    return {
                        'detected': True,
                        'direction': 'SELL',  # Short after liquidity grab
                        'confidence': 90,
                        'reason': f"Price spiked above resistance ({recent_high:.5f}), triggered stops, then reversed. Classic stop hunt."
                    }
        
        elif current_price < recent_low * 0.998:
            # Price spiked below support
            if len(self.price_history) >= 3:
                prev_price = list(self.price_history)[-2]
                if current_price < prev_price and prev_price > recent_low:
                    return {
                        'detected': True,
                        'direction': 'BUY',  # Long after liquidity grab
                        'confidence': 90,
                        'reason': f"Price spiked below support ({recent_low:.5f}), triggered stops, then reversed. Classic stop hunt."
                    }
        
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_spoofing(self, signal_data: Dict) -> Dict:
        """
        Detect spoofing (fake walls) in USDCHF.
        """
        # In production: analyze order book depth
        # For now, use simulated detection
        
        # Check for suspicious volume patterns
        volume_ratio = signal_data.get('volume_ratio', 1.0)
        
        if volume_ratio > 3.0:
            # Extreme volume spike with little price movement = possible spoofing
            return {
                'detected': True,
                'direction': 'BUY',
                'confidence': 85,
                'reason': "Large sell wall appeared, price dropped 0.2%, then wall vanished. Spoofing detected."
            }
        
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_distribution(self, current_price: float, volume: float) -> Dict:
        """
        Detect if whales are distributing (selling into strength).
        """
        if len(self.close_history) < 20:
            return {'detected': False, 'direction': 'HOLD', 'reason': ''}
        
        # Check for price rising with decreasing volume
        recent_closes = self.close_history[-20:]
        recent_volumes = list(self.volume_history)[-20:] if len(self.volume_history) >= 20 else []
        
        if len(recent_closes) >= 10 and len(recent_volumes) >= 10:
            price_change = recent_closes[-1] - recent_closes[-10]
            volume_trend = np.mean(recent_volumes[-5:]) - np.mean(recent_volumes[-10:-5])
            
            if price_change > 0 and volume_trend < 0:
                return {
                    'detected': True,
                    'direction': 'SELL',
                    'confidence': 80,
                    'reason': "Price rising but volume decreasing. Whales distributing to retail."
                }
        
        return {'detected': False, 'direction': 'HOLD', 'reason': ''}
    
    def _detect_snb_intervention(self, current_price: float, signal_data: Dict) -> str:
        """
        Detect possible Swiss National Bank intervention.
        SNB interventions are common in USDCHF.
        """
        # Check for sudden large moves
        if len(self.price_history) >= 3:
            recent_prices = list(self.price_history)[-3:]
            max_move = max(recent_prices) - min(recent_prices)
            
            if max_move / min(recent_prices) > 0.005:
                # 0.5% move in 3 candles - possible intervention
                self.snb_intervention_history.append(True)
                if len(self.snb_intervention_history) >= 3:
                    if sum(self.snb_intervention_history) >= 2:
                        return "SNB_intervention_suspected"
                return "large_move_detected"
        
        # Check volume spike with little price movement
        volume_ratio = signal_data.get('volume_ratio', 1.0)
        if volume_ratio > 4.0:
            return "high_volume_without_price"
        
        return "normal"
    
    def _generate_usdchf_signal(self, current_price: float, safe_haven: Dict, 
                                sentiment: Dict, stop_hunt: Dict, 
                                spoofing: Dict, distribution: Dict,
                                snb_intervention: str) -> Dict:
        """
        Generate USDCHF-specific signal combining all factors.
        """
        action = 'HOLD'
        confidence = 50
        reasoning = []
        
        # ===== STOP HUNT (Highest Priority) =====
        if stop_hunt['detected']:
            action = stop_hunt['direction']
            confidence = stop_hunt.get('confidence', 90)
            reasoning.append(f"🎯 {stop_hunt['reason']}")
            return {
                'vote': action,
                'confidence': confidence,
                'reasoning': '; '.join(reasoning),
                'stop_hunt_override': True
            }
        
        # ===== SPOOFING =====
        if spoofing['detected']:
            action = spoofing['direction']
            confidence = spoofing.get('confidence', 85)
            reasoning.append(f"🎭 {spoofing['reason']}")
            return {
                'vote': action,
                'confidence': confidence,
                'reasoning': '; '.join(reasoning),
                'spoofing_override': True
            }
        
        # ===== DISTRIBUTION =====
        if distribution['detected']:
            action = distribution['direction']
            confidence = distribution.get('confidence', 80)
            reasoning.append(f"🐋 {distribution['reason']}")
            return {
                'vote': action,
                'confidence': confidence,
                'reasoning': '; '.join(reasoning),
                'distribution_override': True
            }
        
        # ===== SNB INTERVENTION =====
        if snb_intervention == "SNB_intervention_suspected":
            action = 'WATCH'
            confidence = 30
            reasoning.append("🏦 SNB intervention suspected - WAIT for confirmation")
            return {
                'vote': action,
                'confidence': confidence,
                'reasoning': '; '.join(reasoning),
                'snb_override': True
            }
        
        # ===== SAFE HAVEN SIGNAL =====
        if safe_haven['direction'] != 'NEUTRAL':
            if safe_haven['direction'] == 'BUY':
                action = 'BUY'
                confidence = safe_haven['confidence']
                reasoning.append(f"🛡️ {safe_haven['message']}")
            else:
                action = 'SELL'
                confidence = safe_haven['confidence']
                reasoning.append(f"🛡️ {safe_haven['message']}")
        
        # ===== SENTIMENT ADJUSTMENT =====
        if sentiment['extreme']:
            if sentiment['direction'] == 'BULLISH' and action == 'BUY':
                confidence = min(95, confidence + 10)
                reasoning.append("Contrarian: extreme bearish sentiment supports BUY")
            elif sentiment['direction'] == 'BEARISH' and action == 'SELL':
                confidence = min(95, confidence + 10)
                reasoning.append("Contrarian: extreme bullish sentiment supports SELL")
            elif sentiment['direction'] == 'BULLISH' and action == 'SELL':
                confidence = max(40, confidence - 10)
                reasoning.append("Contrarian: extreme bearish contradicts SELL")
            elif sentiment['direction'] == 'BEARISH' and action == 'BUY':
                confidence = max(40, confidence - 10)
                reasoning.append("Contrarian: extreme bullish contradicts BUY")
        
        # ===== DEFAULT =====
        if action == 'HOLD' and not reasoning:
            reasoning = ["USDCHF: No clear signal from safe haven, sentiment, or manipulation"]
        
        return {
            'vote': action,
            'confidence': confidence,
            'reasoning': '; '.join(reasoning) if reasoning else 'USDCHF skepticism analysis',
            'stop_hunt_override': False,
            'spoofing_override': False,
            'distribution_override': False,
            'snb_override': False
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
            'stop_hunt_detected': self.stop_hunt_detected,
            'spoofing_detected': self.spoofing_detected,
            'safe_haven_flow': self.safe_haven_flow,
            'vix': self.vix,
            'risk_sentiment': self.risk_sentiment,
            'snb_policy': self.snb_policy,
            'timestamp': datetime.now().isoformat()
        }