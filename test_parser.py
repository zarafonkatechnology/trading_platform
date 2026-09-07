#!/usr/bin/env python3
"""
Test the signal parser with different formats
"""

import re
from datetime import datetime

class QuickParser:
    @staticmethod
    def parse(message):
        print(f"\nTesting: {message}")
        
        # Find price (any number with optional $)
        price_match = re.search(r'\$?(\d+(?:\.\d+)?)', message)
        if price_match:
            price = float(price_match.group(1))
            print(f"  ✅ Price found: ${price}")
        else:
            print(f"  ❌ No price found")
            return None
        
        # Find asset (word before price or at beginning)
        asset_match = re.search(r'^([A-Z]+)', message)
        if asset_match:
            asset = asset_match.group(1)
            print(f"  ✅ Asset found: {asset}")
        
        # Find confidence
        conf_match = re.search(r'(\d+)%', message)
        if conf_match:
            confidence = int(conf_match.group(1))
            print(f"  ✅ Confidence: {confidence}%")
        
        # Find SL
        sl_match = re.search(r'SL:\s*\$?(\d+(?:\.\d+)?)', message, re.IGNORECASE)
        if sl_match:
            sl = float(sl_match.group(1))
            print(f"  ✅ Stop Loss: ${sl}")
        
        # Find TP
        tp_match = re.search(r'TP:\s*\$?(\d+(?:\.\d+)?)', message, re.IGNORECASE)
        if tp_match:
            tp = float(tp_match.group(1))
            print(f"  ✅ Take Profit: ${tp}")
        
        return True

# Test different formats
test_messages = [
    "GOLD 2350.50",
    "GOLD $2350.50",
    "GOLD: $2350.50",
    "GOLD $2350.50 Confidence: 85%",
    "GOLD $2350.50 SL 2340 TP 2370",
    "GOLD: $2350.50 | Confidence: 85% | STRONG SIGNAL",
]

print("=" * 50)
print("TESTING SIGNAL PARSER")
print("=" * 50)

for msg in test_messages:
    QuickParser.parse(msg)

print("\n" + "=" * 50)
