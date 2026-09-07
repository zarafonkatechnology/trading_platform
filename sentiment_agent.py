# sentiment_agent.py - SIMPLIFIED VERSION
"""
Agent_I - Sentiment Master
NLP-based news and social media sentiment
"""

import random
from datetime import datetime
from typing import Dict

class SentimentMaster:
    """Agent I - Sentiment Analysis Master"""
    
    def __init__(self):
        self.name = "Agent_I"
        self.agent_type = "Sentiment Master"
        self.specialization = "News & Social Media Sentiment Analysis"
        self.news_sources = ['forexfactory', 'dailyfx', 'bloomberg']
        print("   ✅ Sentiment Master initialized")
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Analyze market sentiment from news and social media"""
        
        symbol = signal_data.get('symbol', 'EURUSD')
        
        # Get sentiment score (-100 to +100)
        sentiment_score = self._calculate_sentiment()
        
        # Detect extreme sentiment (contrarian signals)
        is_extreme_bullish = sentiment_score > 80
        is_extreme_bearish = sentiment_score < -80
        
        # Generate vote based on sentiment
        if is_extreme_bullish:
            vote = "SELL"  # Contrarian - sell when everyone is buying
            confidence = 85
            reasoning = f"🔴 EXTREME BULLISH SENTIMENT for {symbol}: Everyone is buying. This is a TOP signal."
        elif is_extreme_bearish:
            vote = "BUY"   # Contrarian - buy when everyone is selling
            confidence = 85
            reasoning = f"🟢 EXTREME BEARISH SENTIMENT for {symbol}: Everyone is selling. This is a BOTTOM signal."
        elif sentiment_score > 30:
            vote = "BUY"
            confidence = min(95, 60 + sentiment_score * 0.3)
            reasoning = f"📰 Bullish sentiment detected for {symbol} ({sentiment_score:.0f}/100)"
        elif sentiment_score < -30:
            vote = "SELL"
            confidence = min(95, 60 + abs(sentiment_score) * 0.3)
            reasoning = f"📰 Bearish sentiment detected for {symbol} ({abs(sentiment_score):.0f}/100)"
        else:
            vote = "HOLD"
            confidence = 50
            reasoning = f"📰 Neutral sentiment for {symbol} ({sentiment_score:.0f}/100)"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'symbol': symbol,
            'vote': vote,
            'confidence': int(confidence),
            'reasoning': reasoning,
            'sentiment_data': {
                'score': sentiment_score,
                'is_extreme_bullish': is_extreme_bullish,
                'is_extreme_bearish': is_extreme_bearish,
                'sentiment_level': 'extreme' if (is_extreme_bullish or is_extreme_bearish) else 'normal',
                'news_count': random.randint(5, 50),
                'social_mentions': random.randint(100, 5000)
            },
            'is_contrarian_signal': is_extreme_bullish or is_extreme_bearish,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_sentiment(self) -> float:
        """Calculate sentiment score from multiple sources"""
        # In production: use NLP on news feeds, Twitter, Reddit
        # For demo: simulated sentiment
        base_sentiment = random.randint(-60, 60)
        trending = random.randint(-15, 15)
        return base_sentiment + trending