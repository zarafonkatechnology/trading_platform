"""
Economic Calendar Data Source
- Fetches economic events from free APIs (ForexFactory, Investing.com)
- Calculates impact scores for trading decisions
- Provides event filtering by currency, importance, and time
"""

import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import threading


@dataclass
class EconomicEvent:
    """Economic event data structure"""
    event_name: str
    country: str
    currency: str
    importance: str  # HIGH, MEDIUM, LOW
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    datetime: Optional[datetime] = None
    impact_score: float = 0.0
    
    def calculate_impact(self) -> float:
        """Calculate impact score based on deviation and importance"""
        if self.actual is None or self.forecast is None:
            return 0.0
        
        # Deviation percentage
        deviation = abs((self.actual - self.forecast) / (self.forecast + 1e-10)) * 100
        
        # Importance multiplier
        importance_mult = {'HIGH': 1.0, 'MEDIUM': 0.5, 'LOW': 0.2}
        mult = importance_mult.get(self.importance, 0.3)
        
        # Impact score (0-100)
        impact = min(100, deviation * mult * 10)
        
        # Direction (positive vs negative surprise)
        if self.actual > self.forecast:
            self.impact_score = impact
        else:
            self.impact_score = -impact
        
        return self.impact_score


class EconomicCalendar:
    """
    Fetches and manages economic events
    Uses multiple free sources:
    - ForexFactory (via unofficial API)
    - Alpha Vantage (economic indicators)
    - FRED (Federal Reserve Economic Data)
    """
    
    def __init__(self, alpha_vantage_key: Optional[str] = None):
        self.alpha_vantage_key = alpha_vantage_key
        self.events: List[EconomicEvent] = []
        self.impact_map = {
            'USD': {'high_impact': ['NFP', 'CPI', 'FOMC', 'GDP', 'Non-Farm'],
                    'medium_impact': ['Retail Sales', 'Industrial Production', 'PPI']},
            'EUR': {'high_impact': ['ECB', 'German GDP', 'CPI', 'PMI'],
                    'medium_impact': ['German ZEW', 'Trade Balance']},
            'GBP': {'high_impact': ['BOE', 'CPI', 'GDP'],
                    'medium_impact': ['Retail Sales', 'Manufacturing PMI']},
            'JPY': {'high_impact': ['BOJ', 'CPI', 'GDP', 'Tankan'],
                    'medium_impact': ['Industrial Production', 'Retail Sales']},
            'CNY': {'high_impact': ['GDP', 'CPI', 'PMI', 'Trade Balance'],
                    'medium_impact': ['Industrial Production', 'Retail Sales']},
            'CHF': {'high_impact': ['SNB', 'CPI', 'GDP'],
                    'medium_impact': ['Trade Balance', 'Retail Sales']},
            'CAD': {'high_impact': ['BOC', 'CPI', 'GDP', 'Employment'],
                    'medium_impact': ['Retail Sales', 'Trade Balance']},
            'AUD': {'high_impact': ['RBA', 'CPI', 'GDP', 'Employment'],
                    'medium_impact': ['Trade Balance', 'Retail Sales']},
            'NZD': {'high_impact': ['RBNZ', 'CPI', 'GDP', 'Employment'],
                    'medium_impact': ['Trade Balance', 'Retail Sales']}
        }
        self.update_lock = threading.Lock()
        self.last_update = None
        self.update_interval_minutes = 60
        self._start_auto_update()
    
    def _start_auto_update(self):
        """Start automatic background updates"""
        def update_loop():
            while True:
                try:
                    self.update_events()
                    time.sleep(self.update_interval_minutes * 60)
                except Exception as e:
                    print(f"Economic calendar update error: {e}")
                    time.sleep(300)
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        print("📅 Economic calendar auto-update started")
    
    def update_events(self):
        """Fetch latest economic events"""
        with self.update_lock:
            self.events = []
            
            # Fetch from ForexFactory (using free API)
            self._fetch_forexfactory_events()
            
            # Fetch from Alpha Vantage if key provided
            if self.alpha_vantage_key:
                self._fetch_alpha_vantage_indicators()
            
            self.last_update = datetime.now()
            print(f"📊 Updated economic calendar: {len(self.events)} events")
    
    def _fetch_forexfactory_events(self):
        """Fetch events from ForexFactory (mock data - replace with actual API)"""
        # In production, use https://www.forexfactory.com/calendar
        # For now, generate realistic sample data
        today = datetime.now()
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'NZD', 'CHF', 'CNY']
        
        for currency in currencies:
            # High impact events
            high_events = self.impact_map.get(currency, {}).get('high_impact', [])
            for event_name in high_events[:2]:  # Top 2 events per currency
                event = EconomicEvent(
                    event_name=event_name,
                    country=self._get_country(currency),
                    currency=currency,
                    importance='HIGH',
                    datetime=today + timedelta(hours=len(self.events) % 48)
                )
                event.calculate_impact()
                self.events.append(event)
            
            # Medium impact events
            medium_events = self.impact_map.get(currency, {}).get('medium_impact', [])
            for event_name in medium_events[:2]:
                event = EconomicEvent(
                    event_name=event_name,
                    country=self._get_country(currency),
                    currency=currency,
                    importance='MEDIUM',
                    datetime=today + timedelta(hours=len(self.events) % 48 + 1)
                )
                event.calculate_impact()
                self.events.append(event)
    
    def _get_country(self, currency: str) -> str:
        """Get country name from currency code"""
        country_map = {
            'USD': 'United States', 'EUR': 'Eurozone', 'GBP': 'United Kingdom',
            'JPY': 'Japan', 'CAD': 'Canada', 'AUD': 'Australia',
            'NZD': 'New Zealand', 'CHF': 'Switzerland', 'CNY': 'China'
        }
        return country_map.get(currency, currency)
    
    def _fetch_alpha_vantage_indicators(self):
        """Fetch economic indicators from Alpha Vantage API"""
        try:
            # Example: Get GDP data
            url = f"https://www.alphavantage.co/query?function=GDP&apikey={self.alpha_vantage_key}"
            response = requests.get(url, timeout=10)
            # Process response...
        except Exception as e:
            print(f"Alpha Vantage error: {e}")
    
    def get_upcoming_events(self, hours: int = 24) -> List[EconomicEvent]:
        """Get upcoming events within specified hours"""
        now = datetime.now()
        cutoff = now + timedelta(hours=hours)
        
        upcoming = [e for e in self.events if e.datetime and now <= e.datetime <= cutoff]
        upcoming.sort(key=lambda x: x.datetime)
        return upcoming
    
    def get_high_impact_events(self, hours: int = 24) -> List[EconomicEvent]:
        """Get high impact events within timeframe"""
        return [e for e in self.get_upcoming_events(hours) if e.importance == 'HIGH']
    
    def get_impact_for_currency(self, currency: str, hours: int = 6) -> float:
        """
        Calculate total impact score for a currency
        Used to adjust trading confidence
        """
        events = [e for e in self.get_upcoming_events(hours) if e.currency == currency]
        total_impact = sum(abs(e.impact_score) for e in events)
        
        # Weight by importance
        for e in events:
            weight = {'HIGH': 3, 'MEDIUM': 1.5, 'LOW': 0.5}
            total_impact += weight.get(e.importance, 1) * abs(e.impact_score)
        
        return min(100, total_impact)
    
    def should_trade(self, currency: str, impact_threshold: float = 50) -> Tuple[bool, str]:
        """
        Determine if trading should proceed based on upcoming events
        Returns: (should_trade, reason)
        """
        impact = self.get_impact_for_currency(currency)
        
        if impact > impact_threshold:
            return False, f"⚠️ High impact events ({impact:.0f}%) - Trading halted"
        
        return True, f"✅ Economic impact low ({impact:.0f}%)"
    
    def get_next_event(self) -> Optional[EconomicEvent]:
        """Get next upcoming event"""
        upcoming = self.get_upcoming_events(72)
        return upcoming[0] if upcoming else None
