# generate_signals.py
"""
Generate Trading Signals for Dashboard
"""

import json
import os
import random
from datetime import datetime
import sys

# ============================================================
# CONFIGURATION
# ============================================================

MT4_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
SIGNALS_FILE = os.path.join(MT4_PATH, "dashboard_signals.json")

# ============================================================
# SYMBOL CONFIG
# ============================================================

SYMBOLS = {
    'EURUSD': {'pip': 0.0001, 'digits': 5, 'price': 1.1355},
    'GBPUSD': {'pip': 0.0001, 'digits': 5, 'price': 1.3164},
    'USDJPY': {'pip': 0.01, 'digits': 3, 'price': 161.83},
    'GOLD': {'pip': 0.1, 'digits': 2, 'price': 3987.55},
    'SILVER': {'pip': 0.01, 'digits': 2, 'price': 57.20},
    '#S&P500': {'pip': 0.1, 'digits': 2, 'price': 7561.37},
    '#DJ30': {'pip': 0.1, 'digits': 2, 'price': 52438.00},
    '#NASDAQ100': {'pip': 0.1, 'digits': 2, 'price': 30208.62},
    'BRENT_OIL': {'pip': 0.01, 'digits': 2, 'price': 75.02},
    'CrudeOIL': {'pip': 0.01, 'digits': 2, 'price': 65.11},
}

# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_realistic_signal(symbol):
    """Generate a realistic trading signal for a symbol"""
    
    config = SYMBOLS[symbol]
    price = config['price']
    pip = config['pip']
    digits = config['digits']
    
    # Randomly decide action (70% HOLD, 15% BUY, 15% SELL for realism)
    rand = random.random()
    
    if rand < 0.15:  # BUY
        action = 'BUY'
        confidence = random.randint(65, 85)
        sl_pips = random.randint(15, 25)
        tp_pips = random.randint(40, 60)
        
        if symbol in ['GOLD', 'SILVER']:
            sl_pips = random.randint(40, 60)
            tp_pips = random.randint(80, 120)
        elif symbol in ['#S&P500', '#DJ30', '#NASDAQ100']:
            sl_pips = random.randint(400, 600)
            tp_pips = random.randint(800, 1200)
        
        sl = price - (sl_pips * pip)
        tp = price + (tp_pips * pip)
        
        reasons = [
            f"Support zone reached with {random.randint(2,4)} bounces",
            f"Bullish divergence detected on {random.choice(['RSI', 'MACD', 'CVD'])}",
            f"Volume spike {random.randint(2,4)}x at demand zone",
            f"Dark pool buying detected: ${random.randint(1,5)}M",
            f"Fibonacci 0.618 retracement support",
            f"Price bounced from {random.randint(2,3)}-year trendline",
            f"Bullish order flow with CVD turning positive",
        ]
        
        reasoning = random.choice(reasons)
        
    elif rand < 0.30:  # SELL
        action = 'SELL'
        confidence = random.randint(65, 85)
        sl_pips = random.randint(15, 25)
        tp_pips = random.randint(40, 60)
        
        if symbol in ['GOLD', 'SILVER']:
            sl_pips = random.randint(40, 60)
            tp_pips = random.randint(80, 120)
        elif symbol in ['#S&P500', '#DJ30', '#NASDAQ100']:
            sl_pips = random.randint(400, 600)
            tp_pips = random.randint(800, 1200)
        
        sl = price + (sl_pips * pip)
        tp = price - (tp_pips * pip)
        
        reasons = [
            f"Resistance zone reached with {random.randint(2,4)} rejections",
            f"Bearish divergence detected on {random.choice(['RSI', 'MACD', 'CVD'])}",
            f"Volume spike {random.randint(2,4)}x at supply zone",
            f"Dark pool selling detected: ${random.randint(1,5)}M",
            f"Fibonacci 0.618 retracement resistance",
            f"Price rejected from {random.randint(2,3)}-year trendline",
            f"Bearish order flow with CVD turning negative",
        ]
        
        reasoning = random.choice(reasons)
        
    else:  # HOLD
        action = 'HOLD'
        confidence = random.randint(40, 60)
        sl = price
        tp = price
        reasoning = "No clear signal - waiting for setup"
    
    # Round values
    entry = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    return {
        'symbol': symbol,
        'action': action,
        'entry_price': entry,
        'stop_loss': sl,
        'take_profit': tp,
        'confidence': confidence,
        'reasoning': reasoning,
        'votes': {
            'BUY': random.randint(10, 80) if action == 'BUY' else random.randint(0, 30),
            'SELL': random.randint(10, 80) if action == 'SELL' else random.randint(0, 30),
            'HOLD': random.randint(10, 50)
        },
        'timestamp': datetime.now().isoformat()
    }

def generate_signals():
    """Generate signals for all symbols"""
    
    signals = []
    
    for symbol in SYMBOLS.keys():
        signal = generate_realistic_signal(symbol)
        # Only include BUY/SELL signals with confidence > 60
        if signal['action'] in ['BUY', 'SELL'] and signal['confidence'] >= 60:
            signals.append(signal)
    
    # Sort by confidence (highest first)
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    return signals

def save_signals(signals):
    """Save signals to file"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(MT4_PATH, exist_ok=True)
        
        with open(SIGNALS_FILE, 'w') as f:
            json.dump(signals, f, indent=2)
        
        print(f"✅ Saved {len(signals)} signals to {SIGNALS_FILE}")
        return True
    except Exception as e:
        print(f"❌ Error saving signals: {e}")
        return False

def clear_signals():
    """Clear all signals"""
    try:
        with open(SIGNALS_FILE, 'w') as f:
            json.dump([], f)
        print("✅ Signals cleared")
    except Exception as e:
        print(f"❌ Error clearing signals: {e}")

def display_signals(signals):
    """Display signals in a nice format"""
    print("\n" + "=" * 60)
    print("📊 ACTIVE TRADING SIGNALS")
    print("=" * 60)
    
    if not signals:
        print("\n📭 No active signals")
        return
    
    for signal in signals:
        color = "🟢" if signal['action'] == 'BUY' else "🔴" if signal['action'] == 'SELL' else "⚪"
        print(f"\n{color} {signal['symbol']} - {signal['action']} ({signal['confidence']}%)")
        print(f"   Entry: {signal['entry_price']}")
        print(f"   SL: {signal['stop_loss']}")
        print(f"   TP: {signal['take_profit']}")
        print(f"   Reason: {signal['reasoning'][:60]}...")
        print(f"   Votes: BUY:{signal['votes']['BUY']}% SELL:{signal['votes']['SELL']}% HOLD:{signal['votes']['HOLD']}%")

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("🎯 SIGNAL GENERATOR")
    print("=" * 60)
    print(f"Signals file: {SIGNALS_FILE}")
    print("=" * 60)
    
    print("\n1. Generate realistic signals")
    print("2. Clear all signals")
    print("3. Display current signals")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ")
    
    if choice == '1':
        signals = generate_signals()
        if save_signals(signals):
            display_signals(signals)
            print("\n✅ Signals generated! Refresh dashboard.")
    elif choice == '2':
        clear_signals()
        print("✅ Signals cleared")
    elif choice == '3':
        try:
            with open(SIGNALS_FILE, 'r') as f:
                signals = json.load(f)
            display_signals(signals)
        except:
            print("❌ No signals file found")
    else:
        print("👋 Exiting...")

if __name__ == "__main__":
    main()