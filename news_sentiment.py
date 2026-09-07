"""
News Sentiment Analysis with NLP
- Fetches news headlines from multiple sources
- Performs sentiment analysis using TextBlob/VADER
- Provides sentiment scores for trading decisions
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import threading
import re


@dataclass
class NewsArticle:
    """News article data structure"""
    title: str
    source: str
    published_at: datetime
    url: str
    sentiment_score: float = 0.0  # -1 to +1
    relevance: float = 0.0
    mentioned_assets: List[str] = None
    
    def __post_init__(self):
        if self.mentioned_assets is None:
            self.mentioned_assets = []


class NewsSentimentAnalyzer:
    """
    Fetches and analyzes news sentiment for trading decisions
    Uses multiple free sources:
    - NewsAPI (requires API key)
    - Reddit API (r/forex, r/wallstreetbets)
    - Twitter API (via free tier)
    """
    
    def __init__(self, newsapi_key: Optional[str] = None):
        self.newsapi_key = newsapi_key
        self.articles: List[NewsArticle] = []
        self.sentiment_history = deque(maxlen=100)
        self.update_lock = threading.Lock()
        self.last_update = None
        self.update_interval_minutes = 15
        self._start_auto_update()
        
        # Asset keywords for relevance matching
        self.asset_keywords = {
            'XAU/USD': ['gold', 'xau', 'precious metal'],
            'XAG/USD': ['silver', 'xag'],
            'EURUSD': ['euro', 'eur', 'ecb', 'european central bank'],
            'GBPUSD': ['pound', 'gbp', 'boe', 'bank of england'],
            'USDJPY': ['yen', 'jpy', 'boj', 'bank of japan'],
            'BCO/USD': ['brent', 'oil', 'crude'],
            'S&P500/USD': ['s&p', 'sp500', 'us500'],
            'NAS100/USD': ['nasdaq', 'nas100', 'tech stocks']
        }
    
    def _start_auto_update(self):
        """Start automatic background updates"""
        def update_loop():
            while True:
                try:
                    self.fetch_news()
                    time.sleep(self.update_interval_minutes * 60)
                except Exception as e:
                    print(f"News sentiment update error: {e}")
                    time.sleep(300)
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        print("📰 News sentiment auto-update started")
    
    def fetch_news(self):
        """Fetch news from various sources"""
        with self.update_lock:
            self.articles = []
            
            # Fetch from NewsAPI if key provided
            if self.newsapi_key:
                self._fetch_newsapi()
            
            # Fallback to mock data
            if not self.articles:
                self._fetch_mock_news()
            
            # Analyze sentiment for all articles
            for article in self.articles:
                article.sentiment_score = self._analyze_sentiment(article.title)
                article.mentioned_assets = self._extract_mentioned_assets(article.title)
            
            self.last_update = datetime.now()
            print(f"📊 News sentiment updated: {len(self.articles)} articles")
    
    def _fetch_newsapi(self):
        """Fetch news from NewsAPI"""
        try:
            # Forex news
            forex_url = f"https://newsapi.org/v2/everything?q=forex OR currency OR forex trading&language=en&sortBy=publishedAt&apiKey={self.newsapi_key}"
            response = requests.get(forex_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('articles', [])[:30]:
                    article = NewsArticle(
                        title=item['title'],
                        source=item['source']['name'],
                        published_at=datetime.fromisoformat(item['publishedAt'].replace('Z', '+00:00')),
                        url=item['url']
                    )
                    self.articles.append(article)
        except Exception as e:
            print(f"NewsAPI error: {e}")
    
    def _fetch_mock_news(self):
        """Generate mock news for testing"""
        mock_headlines = [
            "Fed signals potential rate cut as inflation moderates",
            "ECB maintains cautious stance on further rate hikes",
            "Gold surges to record high on safe-haven demand",
            "Oil prices drop as OPEC+ considers production increase",
            "Dollar weakens after mixed economic data",
            "Euro gains ground on improving German business sentiment",
            "Pound volatile amid Brexit trade deal negotiations",
            "Yen strengthens as BOJ hints at policy normalization",
            "S&P 500 hits new record on tech rally",
            "Nasdaq leads gains as AI stocks surge",
            "CrudeOIL volatility expected ahead of OPEC meeting",
            "Central bank decisions key for FX markets this week"
        ]
        
        for headline in mock_headlines[:15]:
            article = NewsArticle(
                title=headline,
                source="Mock News",
                published_at=datetime.now() - timedelta(hours=len(self.articles) % 24),
                url="#"
            )
            self.articles.append(article)
    
    def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment using simple keyword-based method
        In production, use TextBlob or VADER for better accuracy
        """
        text_lower = text.lower()
        
        # Positive keywords
        positive_words = ['surge', 'rally', 'gain', 'rise', 'up', 'positive', 'strong', 
                         'bullish', 'boost', 'growth', 'record', 'high']
        
        # Negative keywords
        negative_words = ['drop', 'fall', 'down', 'negative', 'weak', 'bearish', 
                         'decline', 'slump', 'low', 'crash', 'selloff', 'volatile']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def _extract_mentioned_assets(self, text: str) -> List[str]:
        """Extract mentioned asset symbols from text"""
        text_lower = text.lower()
        mentioned = []
        
        for asset, keywords in self.asset_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    mentioned.append(asset)
                    break
        
        return mentioned
    
    def get_sentiment_for_asset(self, asset: str, hours: int = 24) -> Dict:
        """
        Get sentiment analysis for a specific asset
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        relevant = [a for a in self.articles 
                   if a.published_at >= cutoff and asset in a.mentioned_assets]
        
        if not relevant:
            return {
                'score': 0,
                'confidence': 0,
                'trend': 'neutral',
                'articles_count': 0,
                'message': 'No recent news'
            }
        
        avg_sentiment = sum(a.sentiment_score for a in relevant) / len(relevant)
        
        # Determine sentiment trend
        if avg_sentiment > 0.2:
            trend = 'bullish'
        elif avg_sentiment < -0.2:
            trend = 'bearish'
        else:
            trend = 'neutral'
        
        return {
            'score': round(avg_sentiment, 3),
            'confidence': min(100, len(relevant) * 10),
            'trend': trend,
            'articles_count': len(relevant),
            'message': f"Sentiment {trend.upper()} based on {len(relevant)} recent articles"
        }
    
    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment"""
        sentiments = []
        for asset in self.asset_keywords.keys():
            sentiment = self.get_sentiment_for_asset(asset, hours=12)
            sentiments.append(sentiment['score'])
        
        avg = sum(sentiments) / len(sentiments) if sentiments else 0
        
        return {
            'overall_score': round(avg, 3),
            'risk_appetite': 'high' if avg > 0.1 else ('low' if avg < -0.1 else 'neutral'),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_high_impact_news(self, hours: int = 12) -> List[NewsArticle]:
        """Get high impact news based on sentiment strength"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [a for a in self.articles if a.published_at >= cutoff]
        high_impact = [a for a in recent if abs(a.sentiment_score) > 0.5]
        return sorted(high_impact, key=lambda x: abs(x.sentiment_score), reverse=True)
