# forex_price_provider.py - NO FALLBACK, ONLY REAL DATA

import os
import json
from datetime import datetime

# ============ FILE PATHS ============
COMMON_FILES = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/"
MT4_FILES_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"

DASHBOARD_FILE_PATHS = [
    os.path.join(COMMON_FILES, "dashboard_data.json"),
    os.path.join(MT4_FILES_PATH, "dashboard_data.json")
]

# All forex pairs only (since this is for forex)
FOREX_PAIRS = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
    'EURGBP', 'EURJPY', 'EURCAD', 'EURNZD', 'EURCHF'
]


def get_all_prices():
    """Get ALL prices from dashboard file - NO FALLBACK"""
    prices = {}
    
    for file_path in DASHBOARD_FILE_PATHS:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Check if 'prices' key exists
                if 'prices' in data and data['prices']:
                    # Get all forex pairs from the file
                    for pair in FOREX_PAIRS:
                        # Try exact match first
                        if pair in data['prices']:
                            price = data['prices'][pair]
                            if isinstance(price, dict):
                                price = price.get('price', 0)
                            if price and float(price) > 0:
                                prices[pair] = float(price)
                        # Try alternative names
                        elif pair == 'USDCHF' and 'CHF' in data['prices']:
                            price = data['prices']['CHF']
                            if isinstance(price, dict):
                                price = price.get('price', 0)
                            if price and float(price) > 0:
                                prices[pair] = float(price)
                
                # Also check direct keys (if prices are at root level)
                for pair in FOREX_PAIRS:
                    if pair not in prices and pair in data:
                        price = data[pair]
                        if isinstance(price, dict):
                            price = price.get('price', 0)
                        if price and float(price) > 0:
                            prices[pair] = float(price)
                
                # If we found any prices, return them
                if prices:
                    print(f"✅ Got {len(prices)} forex prices from {file_path}")
                    return prices
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
    
    # NO FALLBACK - return empty dict if no real prices found
    print("⚠️ No real forex prices found in any dashboard file")
    return prices


def get_account_info():
    """Get account info from dashboard file - NO FALLBACK"""
    for file_path in DASHBOARD_FILE_PATHS:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                balance = data.get('balance', 0)
                equity = data.get('equity', 0)
                margin = data.get('margin', 0)
                free_margin = data.get('free_margin', 0)
                
                if balance > 0 or equity > 0:
                    return {
                        'balance': float(balance),
                        'equity': float(equity),
                        'margin': float(margin),
                        'free_margin': float(free_margin)
                    }
            except Exception as e:
                print(f"Error reading account from {file_path}: {e}")
                continue
    
    # NO FALLBACK - return zeros
    return {
        'balance': 0,
        'equity': 0,
        'margin': 0,
        'free_margin': 0
    }


def get_price(symbol):
    """Get price for a single symbol - NO FALLBACK"""
    prices = get_all_prices()
    return prices.get(symbol, 0)