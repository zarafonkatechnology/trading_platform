"""
Agent_I - Sentiment Master
NLP-based news and social media sentiment
Enhanced with Velocity Filter + Adaptive Threshold + Real Data Support
"""

import logging
import random
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import deque

# Try imports with fallbacks
try:
    from backend.agents.base_agent import BaseAgent
except ImportError:
    try:
        from agents.base_agent import BaseAgent
    except ImportError:
        class BaseAgent:
            def __init__(self, name="BaseAgent", agent_type="General", specialization="General"):
                self.name = name
                self.agent_type = agent_type
                self.specialization = specialization
                self.xp_points = 0
                self.token_balance = 0
                self.trust_weight = 1.0

# Price imports with fallbacks
try:
    from price_cache_manager import get_price_for_agent, get_any_price, price_cache
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    def get_price_with_fallback(symbol, agent_name):
        return 0
    def get_any_price(symbol):
        return None
    class price_cache:
        @staticmethod
        def get_price(symbol, use_cache_fallback=True):
            return None
        @staticmethod
        def get_cached_price(symbol):
            return None

# Try real sentiment API imports
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

logger = logging.getLogger(__name__)


# ============================================================
# VELOCITY FILTER
# ============================================================

class VelocityFilter:
    """Prevents premature entries when momentum is still building."""
    
    def __init__(self, window: int = 5):
        self.window = window
        self.price_history = []
        self.velocity_history = []
    
    def update(self, price: float) -> Dict:
        self.price_history.append(price)
        if len(self.price_history) > self.window + 1:
            self.price_history.pop(0)
        
        if len(self.price_history) < 3:
            return {
                'velocity': 0.0,
                'momentum': 'STABLE',
                'is_accelerating': False,
                'can_enter': False
            }
        
        velocities = [self.price_history[i] - self.price_history[i-1] 
                      for i in range(1, len(self.price_history))]
        current_velocity = velocities[-1]
        self.velocity_history.append(current_velocity)
        
        if len(velocities) >= 2:
            acceleration = velocities[-1] - velocities[-2]
            is_accelerating = (current_velocity > 0 and acceleration > 0) or \
                              (current_velocity < 0 and acceleration < 0)
        else:
            acceleration = 0.0
            is_accelerating = False
        
        if current_velocity > 0.1:
            momentum = 'RISING'
        elif current_velocity < -0.1:
            momentum = 'FALLING'
        else:
            momentum = 'STABLE'
        
        can_enter = abs(current_velocity) < 0.05 or is_accelerating
        
        return {
            'velocity': current_velocity,
            'momentum': momentum,
            'is_accelerating': is_accelerating,
            'can_enter': can_enter
        }


# ============================================================
# REAL SENTIMENT DATA FETCHER
# ============================================================

class SentimentDataFetcher:
    """
    Fetches real sentiment data from various sources.
    Supports: News APIs, Social Media APIs, Fear & Greed Index
    """
    
    def __init__(self, api_key: str = None, source: str = 'simulated'):
        self.api_key = api_key
        self.source = source
        self.cache = {}
    
    def fetch_sentiment(self, symbol: str) -> Dict:
        """Fetch sentiment data from configured source."""
        if self.source == 'newsapi' and self.api_key:
            return self._fetch_newsapi(symbol)
        elif self.source == 'fear_greed':
            return self._fetch_fear_greed()
        else:
            return self._fetch_simulated(symbol)
    
    def _fetch_newsapi(self, symbol: str) -> Dict:
        """Fetch sentiment from NewsAPI."""
        if not REQUESTS_AVAILABLE:
            return self._fetch_simulated(symbol)
        
        try:
            url = f"https://newsapi.org/v2/everything"
            params = {
                'apiKey': self.api_key,
                'q': symbol,
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                # Simple sentiment analysis (placeholder)
                positive = sum(1 for a in articles if 'up' in a.get('title', '').lower())
                negative = sum(1 for a in articles if 'down' in a.get('title', '').lower())
                
                total = len(articles) if articles else 1
                score = ((positive - negative) / total) * 100
                
                return {
                    'score': max(-100, min(100, score)),
                    'source': 'NEWSAPI',
                    'articles': len(articles),
                    'positive_count': positive,
                    'negative_count': negative
                }
            else:
                return self._fetch_simulated(symbol)
                
        except Exception as e:
            logger.warning(f"NewsAPI error: {e}")
            return self._fetch_simulated(symbol)
    
    def _fetch_fear_greed(self) -> Dict:
        """Fetch Fear & Greed Index."""
        if not REQUESTS_AVAILABLE:
            return self._fetch_simulated('SP500')
        
        try:
            # Alternative: CNN Fear & Greed Index
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and len(data['data']) > 0:
                    value = int(data['data'][0]['value'])
                    # Map 0-100 to -100 to +100
                    score = (value - 50) * 2
                    return {
                        'score': max(-100, min(100, score)),
                        'source': 'FEAR_GREED',
                        'fear_greed_value': value,
                        'fear_greed_label': data['data'][0].get('value_classification', 'Neutral')
                    }
            return self._fetch_simulated('SP500')
            
        except Exception as e:
            logger.warning(f"Fear & Greed error: {e}")
            return self._fetch_simulated('SP500')
    
    def _fetch_simulated(self, symbol: str) -> Dict:
        """Generate simulated sentiment data."""
        # More realistic sentiment with trends
        base = random.randint(-60, 60)
        
        # Add momentum (sentiment tends to persist)
        if hasattr(self, '_last_score'):
            base = int(base * 0.6 + self._last_score * 0.4)
        
        score = max(-100, min(100, base))
        self._last_score = score
        
        return {
            'score': score,
            'source': 'SIMULATED',
            'articles': random.randint(5, 50),
            'social_mentions': random.randint(100, 5000),
            'trending': random.choice(['rising', 'falling', 'stable'])
        }


class SentimentMaster(BaseAgent):
    """
    Agent_I - Sentiment Analysis Master
    Enhanced with Velocity Filter + Adaptive Threshold + Real Data
    """
    
    def __init__(self, api_key: str = None, data_source: str = 'simulated'):
        super().__init__(
            name="Agent_I",
            agent_type="Sentiment Master",
            specialization="News & Social Media Sentiment Analysis"
        )
        
        # ===== SENTIMENT DATA =====
        self.data_fetcher = SentimentDataFetcher(api_key=api_key, source=data_source)
        self.sentiment_history = deque(maxlen=50)
        self.last_sentiment_score = 0
        
        # ===== VELOCITY FILTER =====
        self.velocity_filter = VelocityFilter(window=5)
        
        # ===== ADAPTIVE THRESHOLD =====
        self.base_extreme_threshold = 80
        self.current_extreme_threshold = 80
        
        # ===== STATE =====
        self.last_signal = 'HOLD'
        self.last_confidence = 50
        self.contrarian_signals = 0
        
        # ===== STATISTICS =====
        self.signals_generated = 0
        self.extreme_signals_detected = 0
        
        # ===== PRICE CACHE =====
        self._price_cache = {}
        
        # ===== NEWS SOURCES =====
        self.news_sources = ['forexfactory', 'dailyfx', 'bloomberg']
        
        logger.info(f"   ✅ {self.name} (Sentiment Master) initialized")
        logger.info(f"      📊 Data Source: {data_source}")
        logger.info(f"      📊 Velocity Filter: Active")
        logger.info(f"      📊 Adaptive Threshold: Active")
    
    # ============================================================
    # PRICE RETRIEVAL
    # ============================================================
    
    def get_current_price(self, symbol: str) -> float:
        if symbol in self._price_cache:
            cached_time, cached_price = self._price_cache[symbol]
            if (datetime.now() - cached_time).seconds < 10:
                return cached_price
        
        try:
            price = get_price_with_fallback(symbol, self.name)
            if price > 0:
                self._price_cache[symbol] = (datetime.now(), price)
                return price
        except:
            pass
        
        return 0.0
    
    # ============================================================
    # ADAPTIVE THRESHOLD
    # ============================================================
    
    def _get_adaptive_threshold(self, volatility: float) -> float:
        """
        Calculate adaptive extreme threshold based on volatility.
        Higher volatility → need more extreme sentiment to trigger.
        """
        if volatility < 0.005:
            return 75  # Lower threshold in low volatility
        elif volatility < 0.015:
            return 80  # Default
        elif volatility < 0.03:
            return 85  # Higher in high volatility
        else:
            return 90  # Much higher in extreme volatility
    
    # ============================================================
    # SENTIMENT CALCULATION
    # ============================================================
    
    def _calculate_sentiment(self, symbol: str) -> Dict:
        """Calculate sentiment from multiple sources."""
        # Fetch from data source
        data = self.data_fetcher.fetch_sentiment(symbol)
        
        score = data.get('score', 0)
        self.sentiment_history.append(score)
        self.last_sentiment_score = score
        
        # Determine sentiment level
        if score > 80:
            level = 'extreme_bullish'
        elif score > 50:
            level = 'bullish'
        elif score > 20:
            level = 'moderately_bullish'
        elif score > -20:
            level = 'neutral'
        elif score > -50:
            level = 'moderately_bearish'
        elif score > -80:
            level = 'bearish'
        else:
            level = 'extreme_bearish'
        
        return {
            'score': score,
            'level': level,
            'data': data
        }
    
    def _get_sentiment_momentum(self) -> float:
        """Calculate sentiment momentum (rate of change)."""
        if len(self.sentiment_history) < 5:
            return 0
        
        recent = list(self.sentiment_history)
        current = recent[-1]
        previous = recent[-5] if len(recent) >= 5 else recent[0]
        
        return current - previous
    
    # ============================================================
    # MAIN ANALYSIS
    # ============================================================
    
    def analyze(self, signal_data: Dict) -> Dict:
        """
        Analyze market sentiment from news and social media.
        """
        try:
            # ===== GET SYMBOL & PRICE =====
            symbol = signal_data.get('symbol', signal_data.get('pair', 'UNKNOWN'))
            current_price = signal_data.get('price', 0)
            volatility = signal_data.get('volatility', 0.01)
            
            if current_price <= 0:
                current_price = self.get_current_price(symbol)
            
            if current_price <= 0:
                return self._hold_response("No price available")
            
            # ===== ADAPTIVE THRESHOLD =====
            self.current_extreme_threshold = self._get_adaptive_threshold(volatility)
            
            # ===== VELOCITY FILTER =====
            velocity_result = self.velocity_filter.update(current_price)
            
            # ===== CALCULATE SENTIMENT =====
            sentiment_data = self._calculate_sentiment(symbol)
            sentiment_score = sentiment_data['score']
            sentiment_level = sentiment_data['level']
            
            # ===== SENTIMENT MOMENTUM =====
            sentiment_momentum = self._get_sentiment_momentum()
            
            # ===== GENERATE SIGNAL =====
            vote = 'HOLD'
            confidence = 50
            reasoning = []
            
            # ===== RULE 1: EXTREME SENTIMENT (CONTRARIAN) =====
            if sentiment_score > self.current_extreme_threshold:
                # Extreme bullish → SELL (contrarian)
                vote = 'SELL'
                confidence = min(95, 85 + (sentiment_score - self.current_extreme_threshold) * 0.5)
                reasoning.append(f"🔴 EXTREME BULLISH: {sentiment_score:.0f} > {self.current_extreme_threshold} - SELL signal")
                self.extreme_signals_detected += 1
                self.signals_generated += 1
                
            elif sentiment_score < -self.current_extreme_threshold:
                # Extreme bearish → BUY (contrarian)
                vote = 'BUY'
                confidence = min(95, 85 + (abs(sentiment_score) - self.current_extreme_threshold) * 0.5)
                reasoning.append(f"🟢 EXTREME BEARISH: {abs(sentiment_score):.0f} > {self.current_extreme_threshold} - BUY signal")
                self.extreme_signals_detected += 1
                self.signals_generated += 1
            
            # ===== RULE 2: STRONG SENTIMENT (Directional) =====
            elif sentiment_score > 50:
                vote = 'BUY'
                confidence = 60 + sentiment_score * 0.3
                reasoning.append(f"📰 Bullish sentiment: {sentiment_score:.0f}/100")
                
            elif sentiment_score < -50:
                vote = 'SELL'
                confidence = 60 + abs(sentiment_score) * 0.3
                reasoning.append(f"📰 Bearish sentiment: {abs(sentiment_score):.0f}/100")
            
            # ===== RULE 3: SENTIMENT MOMENTUM =====
            elif abs(sentiment_momentum) > 20:
                if sentiment_momentum > 0 and vote == 'HOLD':
                    vote = 'BUY'
                    confidence = 55 + abs(sentiment_momentum) * 0.2
                    reasoning.append(f"📈 Sentiment rising: {sentiment_momentum:.0f} points")
                elif sentiment_momentum < 0 and vote == 'HOLD':
                    vote = 'SELL'
                    confidence = 55 + abs(sentiment_momentum) * 0.2
                    reasoning.append(f"📉 Sentiment falling: {abs(sentiment_momentum):.0f} points")
            
            # ===== RULE 4: NEUTRAL =====
            if vote == 'HOLD' and not reasoning:
                reasoning.append(f"📰 Neutral sentiment: {sentiment_score:.0f}/100")
            
            # ===== VELOCITY OVERRIDE =====
            if vote != 'HOLD':
                if velocity_result['momentum'] == 'RISING' and vote == 'SELL':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity rising - selling against momentum")
                        vote = 'HOLD'
                elif velocity_result['momentum'] == 'FALLING' and vote == 'BUY':
                    if velocity_result['is_accelerating']:
                        confidence = max(40, confidence - 20)
                        reasoning.append("⚠️ Velocity falling - buying against momentum")
                        vote = 'HOLD'
            
            # ===== STORE STATE =====
            self.last_signal = vote
            self.last_confidence = confidence
            
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': vote,
                'confidence': round(confidence, 1),
                'reasoning': '; '.join(reasoning) if reasoning else 'No sentiment signal',
                'sentiment_data': {
                    'score': sentiment_score,
                    'level': sentiment_level,
                    'momentum': sentiment_momentum,
                    'is_extreme': abs(sentiment_score) > self.current_extreme_threshold,
                    'extreme_threshold': self.current_extreme_threshold,
                },
                'is_contrarian_signal': abs(sentiment_score) > self.current_extreme_threshold,
                'velocity': velocity_result,
                'adaptive_threshold': self.current_extreme_threshold,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"{self.name} analysis error: {e}")
            return self._hold_response(f"Error: {str(e)}")
    
    def _hold_response(self, reason: str) -> Dict:
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 30,
            'reasoning': reason,
            'sentiment_data': None,
            'is_contrarian_signal': False,
            'velocity': None,
            'adaptive_threshold': self.current_extreme_threshold if hasattr(self, 'current_extreme_threshold') else 80,
            'timestamp': datetime.now().isoformat()
        }
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                             n_sims: int = 1000, horizon: int = 20) -> Dict:
        import random
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
            
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
            
            if price > cloud_top:
                outcomes['above_cloud'] += 1
            elif price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        if probs['above_cloud'] > 60:
            vote = 'BUY'
            conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
        
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    
    def get_status(self) -> Dict:
        return {
            'name': self.name,
            'type': self.agent_type,
            'signals_generated': self.signals_generated,
            'extreme_signals_detected': self.extreme_signals_detected,
            'adaptive_threshold': self.current_extreme_threshold if hasattr(self, 'current_extreme_threshold') else 80,
            'last_sentiment': self.last_sentiment_score,
            'last_signal': self.last_signal,
            'last_confidence': self.last_confidence,
            'sentiment_history': len(self.sentiment_history),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# REMOVE AgentP (should be in separate file)
# ============================================================