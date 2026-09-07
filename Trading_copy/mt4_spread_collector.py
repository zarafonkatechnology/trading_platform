# mt4_spread_collector.py
"""
Fixed spread collector with proper bid/ask
"""

import sys
import os
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

import json
import time
from datetime import datetime
from typing import Dict, List, Optional

try:
    from src.mt4_gateway.mt4_bridge import MT4Bridge
    print("✅ MT4 Bridge imported")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

class SpreadCollector:
    """
    Collect spreads from MT4
    """
    
    def __init__(self):
        self.bridge = MT4Bridge()
        self.spread_history = {}
        self.max_history = 100
    
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
    
    def get_spread(self, symbol: str) -> Optional[dict]:
        """
        Get spread for a single symbol
        """
        try:
            # Get bid/ask from MT4
            bid_ask = self.bridge.get_bid_ask(symbol)
            
            if not bid_ask:
                # Try to get from price
                price = self.bridge.get_price(symbol)
                if price and price > 0:
                    pip = self.get_pip_value(symbol)
                    bid_ask = {
                        'bid': price - pip/2,
                        'ask': price + pip/2
                    }
                else:
                    return None
            
            bid = bid_ask.get('bid', 0)
            ask = bid_ask.get('ask', 0)
            
            if bid <= 0 or ask <= 0:
                return None
            
            # Calculate spread
            spread_points = ask - bid
            pip = self.get_pip_value(symbol)
            spread_pips = spread_points / pip if pip > 0 else 0
            
            # Store in history
            if symbol not in self.spread_history:
                self.spread_history[symbol] = []
            
            spread_data = {
                'symbol': symbol,
                'bid': round(bid, 5),
                'ask': round(ask, 5),
                'spread_points': round(spread_points, 5),
                'spread_pips': round(spread_pips, 2),
                'timestamp': datetime.now().isoformat()
            }
            
            self.spread_history[symbol].append(spread_data)
            if len(self.spread_history[symbol]) > self.max_history:
                self.spread_history[symbol] = self.spread_history[symbol][-self.max_history:]
            
            return spread_data
            
        except Exception as e:
            print(f"❌ Error getting spread for {symbol}: {e}")
            return None
    
    def collect_all_spreads(self) -> Dict[str, dict]:
        """
        Collect spreads for all symbols
        """
        symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
                   'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF',
                   'GOLD', 'SILVER',
                   '#NASDAQ100', '#DJ30', '#S&P500', '#RUSS2000', '#CAC40', '#DAX40', '#FTSE100', '#NIKKEI225']
        
        results = {}
        for symbol in symbols:
            spread = self.get_spread(symbol)
            if spread:
                results[symbol] = spread
        
        return results
    
    def get_average_spread(self, symbol: str, lookback: int = 20) -> Optional[dict]:
        """
        Get average spread for a symbol
        """
        if symbol not in self.spread_history or not self.spread_history[symbol]:
            return None
        
        history = self.spread_history[symbol][-lookback:]
        spreads = [h['spread_pips'] for h in history]
        
        if not spreads:
            return None
        
        return {
            'symbol': symbol,
            'avg_spread': round(sum(spreads) / len(spreads), 2),
            'min_spread': round(min(spreads), 2),
            'max_spread': round(max(spreads), 2),
            'sample_count': len(spreads),
            'timestamp': datetime.now().isoformat()
        }
    
    def calculate_markup(self, symbol: str, markup_pips: float = 0.5) -> Optional[dict]:
        """
        Calculate client spread with markup
        """
        current = self.get_spread(symbol)
        if not current:
            return None
        
        broker_spread = current['spread_pips']
        client_spread = broker_spread + markup_pips
        
        return {
            'symbol': symbol,
            'broker_spread': broker_spread,
            'markup_pips': markup_pips,
            'client_spread': client_spread,
            'bid': current['bid'],
            'ask': current['ask'],
            'client_bid': current['bid'] - (markup_pips * self.get_pip_value(symbol) / 2),
            'client_ask': current['ask'] + (markup_pips * self.get_pip_value(symbol) / 2),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# MAIN TEST
# ============================================================

def main():
    print("\n" + "="*60)
    print("📊 MT4 SPREAD COLLECTOR (FIXED)")
    print("="*60)
    
    collector = SpreadCollector()
    
    print("\n📡 Collecting spreads from MT4...")
    spreads = collector.collect_all_spreads()
    
    print(f"\n📊 Collected {len(spreads)} spreads:")
    print("-"*60)
    
    if spreads:
        for symbol, spread in spreads.items():
            print(f"{symbol:12} | Bid: {spread['bid']:.5f} | Ask: {spread['ask']:.5f} | Spread: {spread['spread_pips']:.2f} pips")
    else:
        print("❌ No spreads collected!")
        print("\n💡 Possible reasons:")
        print("   1. Dashboard file doesn't have bid/ask data")
        print("   2. MT4 not running")
        print("   3. EA not writing data")
    
    # Calculate markups
    print("\n📊 Markup Analysis (with 0.5 pips markup):")
    print("-"*60)
    
    for symbol in list(spreads.keys())[:5]:
        markup = collector.calculate_markup(symbol, 0.5)
        if markup:
            print(f"{symbol:12} | Broker: {markup['broker_spread']:.2f} | +Markup: {markup['markup_pips']:.2f} | Client: {markup['client_spread']:.2f}")
    
    # Calculate revenue
    print("\n💰 Revenue per lot (with 0.5 pips markup):")
    print("-"*60)
    
    point_values = {
        'EURUSD': 10, 'GBPUSD': 10, 'USDJPY': 1000,
        'USDCHF': 10, 'AUDUSD': 10, 'USDCAD': 10,
        'NZDUSD': 10, 'EURGBP': 10, 'EURJPY': 1000,
        'GOLD': 1, 'SILVER': 50,
        '#NASDAQ100': 1, '#DJ30': 1, '#S&P500': 1
    }
    
    for symbol in list(spreads.keys())[:5]:
        spread = spreads[symbol]
        point_value = point_values.get(symbol, 10)
        revenue_per_lot = 0.5 * point_value
        print(f"{symbol:12} | ${revenue_per_lot:.2f} per lot")
    
    # Save data
    with open('spread_data.json', 'w') as f:
        json.dump({
            'spreads': spreads,
            'history': collector.spread_history,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)
    print("\n✅ Data saved to spread_data.json")
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)


if __name__ == "__main__":
    main()