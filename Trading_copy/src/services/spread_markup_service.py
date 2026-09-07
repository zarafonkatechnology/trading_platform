# src/services/spread_markup_service.py
"""
Spread Markup Service - Complete Implementation
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SpreadConfig:
    """Configuration for spread markup per symbol"""
    symbol: str
    markup_pips: float
    min_client_spread: float
    max_client_spread: float
    is_active: bool = True

class SpreadMarkupService:
    """
    Service to add markup to spreads and track revenue
    """
    
    def __init__(self):
        # Default markup configuration
        self.default_markup = 0.5  # 0.5 pips markup
        
        # Per-symbol configuration
        self.configs = {
            # Forex - 0.5 pips markup
            'EURUSD': SpreadConfig('EURUSD', 0.5, 0.5, 3.0),
            'GBPUSD': SpreadConfig('GBPUSD', 0.5, 0.5, 3.0),
            'USDJPY': SpreadConfig('USDJPY', 0.5, 0.5, 3.0),
            'USDCHF': SpreadConfig('USDCHF', 0.5, 0.5, 3.0),
            'AUDUSD': SpreadConfig('AUDUSD', 0.5, 0.5, 3.0),
            'USDCAD': SpreadConfig('USDCAD', 0.5, 0.5, 3.0),
            'NZDUSD': SpreadConfig('NZDUSD', 0.5, 0.5, 3.0),
            'EURGBP': SpreadConfig('EURGBP', 0.5, 0.5, 3.0),
            'EURJPY': SpreadConfig('EURJPY', 0.5, 0.5, 3.0),
            'EURCAD': SpreadConfig('EURCAD', 0.5, 0.5, 3.0),
            'EURNZD': SpreadConfig('EURNZD', 0.5, 0.5, 3.0),
            'EURCHF': SpreadConfig('EURCHF', 0.5, 0.5, 3.0),
            
            # Metals - 0.5 pips markup
            'GOLD': SpreadConfig('GOLD', 0.5, 0.5, 5.0),
            'SILVER': SpreadConfig('SILVER', 0.5, 0.5, 5.0),
            
            # Indices - 1.0 pips markup
            '#NASDAQ100': SpreadConfig('#NASDAQ100', 1.0, 1.0, 10.0),
            '#DJ30': SpreadConfig('#DJ30', 1.0, 1.0, 10.0),
            '#S&P500': SpreadConfig('#S&P500', 1.0, 1.0, 10.0),
            '#RUSS2000': SpreadConfig('#RUSS2000', 1.0, 1.0, 10.0),
            '#CAC40': SpreadConfig('#CAC40', 1.0, 1.0, 10.0),
            '#DAX40': SpreadConfig('#DAX40', 1.0, 1.0, 10.0),
            '#FTSE100': SpreadConfig('#FTSE100', 1.0, 1.0, 10.0),
            '#NIKKEI225': SpreadConfig('#NIKKEI225', 1.0, 1.0, 10.0),
            
            # Energy - 1.0 pips markup
            'BRENT_OIL': SpreadConfig('BRENT_OIL', 1.0, 1.0, 10.0),
            'CrudeOIL': SpreadConfig('CrudeOIL', 1.0, 1.0, 10.0),
        }
        
        # Revenue tracking
        self.total_revenue = 0.0
        self.revenue_by_symbol = {}
        self.revenue_by_client = {}
        
        logger.info("✅ Spread Markup Service initialized")
    
    def get_config(self, symbol: str) -> SpreadConfig:
        """Get markup config for symbol"""
        if symbol in self.configs:
            return self.configs[symbol]
        return SpreadConfig(symbol, self.default_markup, 0.5, 5.0)
    
    def get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol"""
        pips = {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01,
            'USDCHF': 0.0001, 'AUDUSD': 0.0001, 'USDCAD': 0.0001,
            'NZDUSD': 0.0001, 'EURGBP': 0.0001, 'EURJPY': 0.01,
            'EURCAD': 0.0001, 'EURNZD': 0.0001, 'EURCHF': 0.0001,
            'GOLD': 0.1, 'SILVER': 0.01,
            '#NASDAQ100': 0.1, '#DJ30': 0.1, '#S&P500': 0.1,
            '#RUSS2000': 0.1, '#CAC40': 0.1, '#DAX40': 0.1,
            '#FTSE100': 0.1, '#NIKKEI225': 0.1,
            'BRENT_OIL': 0.01, 'CrudeOIL': 0.01
        }
        return pips.get(symbol, 0.0001)
    
    def get_point_value(self, symbol: str) -> float:
        """Get point value per lot"""
        point_values = {
            'EURUSD': 10, 'GBPUSD': 10, 'USDJPY': 1000,
            'USDCHF': 10, 'AUDUSD': 10, 'USDCAD': 10,
            'NZDUSD': 10, 'EURGBP': 10, 'EURJPY': 1000,
            'EURCAD': 10, 'EURNZD': 10, 'EURCHF': 10,
            'GOLD': 1, 'SILVER': 50,
            '#NASDAQ100': 1, '#DJ30': 1, '#S&P500': 1,
            '#RUSS2000': 1, '#CAC40': 1, '#DAX40': 1,
            '#FTSE100': 1, '#NIKKEI225': 1,
            'BRENT_OIL': 100, 'CrudeOIL': 100
        }
        return point_values.get(symbol, 10)
    
    def calculate_client_spread(self, symbol: str, broker_bid: float, broker_ask: float) -> dict:
        """
        Calculate client spread with markup
        """
        pip = self.get_pip_value(symbol)
        config = self.get_config(symbol)
        
        # Calculate broker spread in pips
        broker_spread_pips = (broker_ask - broker_bid) / pip
        
        # Apply markup
        markup_pips = config.markup_pips
        client_spread_pips = broker_spread_pips + markup_pips
        
        # Ensure within limits
        client_spread_pips = max(client_spread_pips, config.min_client_spread)
        client_spread_pips = min(client_spread_pips, config.max_client_spread)
        
        # Calculate client bid/ask
        half_markup = (markup_pips * pip) / 2
        client_bid = broker_bid - half_markup
        client_ask = broker_ask + half_markup
        
        return {
            'symbol': symbol,
            'broker_bid': round(broker_bid, 5),
            'broker_ask': round(broker_ask, 5),
            'broker_spread_pips': round(broker_spread_pips, 2),
            'markup_pips': markup_pips,
            'client_bid': round(client_bid, 5),
            'client_ask': round(client_ask, 5),
            'client_spread_pips': round(client_spread_pips, 2),
            'pip_value': pip,
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_revenue(self, symbol: str, volume: float, client_spread_pips: float, broker_spread_pips: float) -> dict:
        """Calculate revenue from spread markup"""
        point_value = self.get_point_value(symbol)
        
        markup_pips = client_spread_pips - broker_spread_pips
        revenue_per_lot = markup_pips * point_value
        total_revenue = revenue_per_lot * volume
        
        return {
            'symbol': symbol,
            'volume': volume,
            'markup_pips': round(markup_pips, 2),
            'revenue_per_lot': round(revenue_per_lot, 2),
            'total_revenue': round(total_revenue, 2)
        }
    
    def track_trade_revenue(self, symbol: str, client_id: str, volume: float, 
                           broker_bid: float, broker_ask: float) -> dict:
        """Track revenue from a trade"""
        # Calculate client spread
        spread_data = self.calculate_client_spread(symbol, broker_bid, broker_ask)
        
        # Calculate revenue
        revenue = self.calculate_revenue(
            symbol, 
            volume, 
            spread_data['client_spread_pips'],
            spread_data['broker_spread_pips']
        )
        
        # Track revenue
        self.total_revenue += revenue['total_revenue']
        
        if symbol not in self.revenue_by_symbol:
            self.revenue_by_symbol[symbol] = 0
        self.revenue_by_symbol[symbol] += revenue['total_revenue']
        
        if client_id not in self.revenue_by_client:
            self.revenue_by_client[client_id] = 0
        self.revenue_by_client[client_id] += revenue['total_revenue']
        
        return {
            'spread_data': spread_data,
            'revenue': revenue,
            'total_revenue': round(self.total_revenue, 2)
        }
    
    def get_revenue_summary(self) -> dict:
        """Get revenue summary"""
        return {
            'total_revenue': round(self.total_revenue, 2),
            'by_symbol': self.revenue_by_symbol,
            'by_client': self.revenue_by_client,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_all_client_spreads(self, broker_data: dict) -> dict:
        """Get client spreads for all symbols"""
        results = {}
        for symbol, prices in broker_data.items():
            if 'bid' in prices and 'ask' in prices:
                result = self.calculate_client_spread(symbol, prices['bid'], prices['ask'])
                results[symbol] = result
        return results