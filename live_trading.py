# live_trading.py - COMPLETE SYMBOL-BASED SL/TP

import os
import json
import time
from datetime import datetime
from mt4_price_provider import get_mt4_prices

MT4_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
COMMAND_FILE = os.path.join(MT4_PATH, "AI_Commands.txt")

# ============================================================
# SYMBOL CONFIGURATION - SL/TP IN PIPS
# ============================================================

SYMBOL_CONFIG = {
    # ===== FOREX =====
    'EURUSD': {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 20,      # 20 pips SL
        'tp_pips': 40,      # 40 pips TP (1:2)
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    'GBPUSD': {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 25,      # 25 pips SL (more volatile)
        'tp_pips': 50,      # 50 pips TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    'USDJPY': {
        'pip': 0.01,
        'digits': 3,
        'sl_pips': 25,      # 25 pips SL
        'tp_pips': 50,      # 50 pips TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    'AUDUSD': {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 25,
        'tp_pips': 50,
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    'USDCAD': {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 25,
        'tp_pips': 50,
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    'NZDUSD': {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 30,
        'tp_pips': 60,
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'forex'
    },
    
    # ===== METALS =====
    'GOLD': {
        'pip': 0.1,
        'digits': 2,
        'sl_pips': 50,      # 50 pips = $5.00 on Gold
        'tp_pips': 100,     # 100 pips = $10.00
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'metal'
    },
    'SILVER': {
        'pip': 0.01,
        'digits': 2,
        'sl_pips': 100,     # 100 pips = $1.00 on Silver
        'tp_pips': 200,     # 200 pips = $2.00
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'metal'
    },
    
    # ===== INDICES =====
    '#NASDAQ100': {
        'pip': 0.1,         # 1 pip = 0.1 points
        'digits': 2,
        'sl_pips': 500,     # 50 points SL
        'tp_pips': 1000,    # 100 points TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'index'
    },
    '#DJ30': {
        'pip': 0.1,
        'digits': 2,
        'sl_pips': 800,     # 80 points SL
        'tp_pips': 1600,    # 160 points TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'index'
    },
    '#S&P500': {
        'pip': 0.1,
        'digits': 2,
        'sl_pips': 600,     # 60 points SL
        'tp_pips': 1200,    # 120 points TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'index'
    },
    
    # ===== ENERGY =====
    'BRENT_OIL': {
        'pip': 0.01,
        'digits': 2,
        'sl_pips': 100,     # $1.00 SL
        'tp_pips': 200,     # $2.00 TP
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'energy'
    },
    'CrudeOIL': {
        'pip': 0.01,
        'digits': 2,
        'sl_pips': 100,
        'tp_pips': 200,
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'energy'
    },
}

def get_symbol_config(symbol):
    """Get configuration for a symbol"""
    # Clean symbol name (remove # if present)
    clean_symbol = symbol.replace('#', '')
    
    # Try to find config
    if clean_symbol in SYMBOL_CONFIG:
        return SYMBOL_CONFIG[clean_symbol]
    
    # Try with # if not found
    if symbol in SYMBOL_CONFIG:
        return SYMBOL_CONFIG[symbol]
    
    # Default config
    return {
        'pip': 0.0001,
        'digits': 5,
        'sl_pips': 20,
        'tp_pips': 40,
        'min_volume': 0.01,
        'max_volume': 10.0,
        'type': 'unknown'
    }

def get_current_price(symbol):
    """Get current price from MT4"""
    try:
        mt4 = get_mt4_prices()
        result = mt4._send({"command": "PRICE", "symbol": symbol})
        
        if result and isinstance(result, dict):
            bid = result.get('bid', 0)
            ask = result.get('ask', 0)
            if bid > 0 and ask > 0:
                return {
                    'bid': bid,
                    'ask': ask,
                    'mid': (bid + ask) / 2,
                    'spread': ask - bid
                }
    except Exception as e:
        print(f"⚠️ Price error: {e}")
    
    # Fallback prices
    fallback = {
        'EURUSD': 1.1355,
        'GBPUSD': 1.3164,
        'USDJPY': 161.83,
        'GOLD': 3987.55,
        'SILVER': 57.20,
        '#NASDAQ100': 29465.12,
        '#DJ30': 52272.00,
        '#S&P500': 7486.25,
        'BRENT_OIL': 74.05,
        'CrudeOIL': 70.38,
    }
    price = fallback.get(symbol, 1.0)
    return {'bid': price, 'ask': price, 'mid': price, 'spread': 0}

def place_order(symbol, order_type, volume=None):
    """Place order with symbol-based SL/TP"""
    
    # Get symbol config
    config = get_symbol_config(symbol)
    pip = config['pip']
    digits = config['digits']
    sl_pips = config['sl_pips']
    tp_pips = config['tp_pips']
    
    # Default volume if not specified
    if volume is None:
        volume = config['min_volume']
    
    # Get current price
    price_info = get_current_price(symbol)
    if not price_info:
        print("❌ Cannot get price!")
        return False
    
    # Get entry price
    if order_type == 'BUY':
        price = price_info['ask']
    else:
        price = price_info['bid']
    
    # Calculate SL and TP
    if order_type == 'BUY':
        sl = price - (sl_pips * pip)
        tp = price + (tp_pips * pip)
    else:
        sl = price + (sl_pips * pip)
        tp = price - (tp_pips * pip)
    
    # Round to correct decimals
    price = round(price, digits)
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    # Calculate risk/reward in dollars
    risk_amount = abs(price - sl) * volume * 100000
    reward_amount = abs(tp - price) * volume * 100000
    
    print(f"\n📊 ORDER DETAILS:")
    print("=" * 60)
    print(f"   Symbol:      {symbol}")
    print(f"   Type:        {order_type}")
    print(f"   Timeframe:   M15 (Short-term)")
    print(f"   Volume:      {volume} lots")
    print(f"   Entry:       {price:.{digits}f}")
    print(f"   Stop Loss:   {sl:.{digits}f} ({sl_pips} pips)")
    print(f"   Take Profit: {tp:.{digits}f} ({tp_pips} pips)")
    print(f"   Risk:        ${risk_amount:.2f}")
    print(f"   Reward:      ${reward_amount:.2f}")
    print(f"   Risk/Reward: 1:{tp_pips/sl_pips:.1f}")
    print(f"   Type:        {config['type'].upper()}")
    print("=" * 60)
    
    # Build order command
    order = {
        "command": "ORDER",
        "symbol": symbol,
        "type": order_type,
        "volume": volume,
        "sl": sl,
        "tp": tp
    }
    
    # Confirm
    print(f"\n🚀 Execute {order_type} {symbol}?")
    print(f"   SL: {sl_pips} pips | TP: {tp_pips} pips")
    response = input("   Confirm (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return False
    
    # Send order
    try:
        if os.path.exists(COMMAND_FILE):
            os.remove(COMMAND_FILE)
        
        with open(COMMAND_FILE, 'w') as f:
            json.dump(order, f)
        
        print(f"\n✅ ORDER SENT TO EA!")
        print(f"   Command: {json.dumps(order)}")
        print(f"\n📌 CHECK MT4 TERMINAL → Trade tab")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_symbol_info():
    """Show all symbol configurations"""
    print("\n📊 SYMBOL CONFIGURATIONS:")
    print("=" * 60)
    print(f"{'Symbol':<12} {'SL':<6} {'TP':<6} {'Pip':<8} {'Type':<10}")
    print("-" * 60)
    
    for symbol, config in SYMBOL_CONFIG.items():
        print(f"{symbol:<12} {config['sl_pips']:<6} {config['tp_pips']:<6} {config['pip']:<8} {config['type']:<10}")

def main():
    print("=" * 60)
    print("💹 LIVE TRADING - SYMBOL-BASED SL/TP")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Show symbol info
    show_symbol_info()
    
    # Current prices
    print("\n📊 Current Prices:")
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY', 'GOLD', '#DJ30', 'BRENT_OIL']:
        price_info = get_current_price(symbol)
        if price_info:
            config = get_symbol_config(symbol)
            digits = config['digits']
            print(f"   {symbol}: {price_info['mid']:.{digits}f}")
    
    while True:
        print("\n" + "=" * 60)
        print("📋 MENU")
        print("=" * 60)
        print("   FOREX:")
        print("   1. BUY EURUSD  2. SELL EURUSD")
        print("   3. BUY GBPUSD  4. SELL GBPUSD")
        print("   5. BUY USDJPY  6. SELL USDJPY")
        print("\n   METALS:")
        print("   7. BUY GOLD   8. SELL GOLD")
        print("   9. BUY SILVER 10. SELL SILVER")
        print("\n   INDICES:")
        print("   11. BUY #DJ30  12. SELL #DJ30")
        print("   13. BUY #S&P500 14. SELL #S&P500")
        print("\n   15. Check Positions")
        print("   16. Close All")
        print("   17. Show Symbol Info")
        print("   18. Exit")
        
        choice = input("\nSelect option (1-18): ")
        
        # Map choices to orders
        orders = {
            '1': ('EURUSD', 'BUY'),
            '2': ('EURUSD', 'SELL'),
            '3': ('GBPUSD', 'BUY'),
            '4': ('GBPUSD', 'SELL'),
            '5': ('USDJPY', 'BUY'),
            '6': ('USDJPY', 'SELL'),
            '7': ('GOLD', 'BUY'),
            '8': ('GOLD', 'SELL'),
            '9': ('SILVER', 'BUY'),
            '10': ('SILVER', 'SELL'),
            '11': ('#DJ30', 'BUY'),
            '12': ('#DJ30', 'SELL'),
            '13': ('#S&P500', 'BUY'),
            '14': ('#S&P500', 'SELL'),
        }
        
        if choice in orders:
            symbol, order_type = orders[choice]
            config = get_symbol_config(symbol)
            print(f"\n   {symbol} {order_type}")
            print(f"   SL: {config['sl_pips']} pips | TP: {config['tp_pips']} pips")
            place_order(symbol, order_type)
        
        elif choice == '15':
            check_positions()
        elif choice == '16':
            close_all_positions()
        elif choice == '17':
            show_symbol_info()
        elif choice == '18':
            print("\n👋 Exiting...")
            break
        else:
            print("❌ Invalid choice")
        
        time.sleep(1)

def check_positions():
    """Check open positions"""
    print("\n📊 CHECKING OPEN POSITIONS")
    print("=" * 50)
    try:
        mt4 = get_mt4_prices()
        result = mt4._send({"command": "POSITIONS"})
        if result:
            positions = result.get('positions', [])
            if positions:
                print(f"   Found {len(positions)} open positions:")
                for pos in positions:
                    print(f"   {pos.get('symbol')}: {pos.get('type')} {pos.get('volume')} lots @ {pos.get('price'):.5f}")
                    print(f"      SL: {pos.get('sl', 'N/A')} | TP: {pos.get('tp', 'N/A')}")
                    print(f"      Profit: ${pos.get('profit', 0):.2f}")
            else:
                print("   No open positions")
    except Exception as e:
        print(f"❌ Error: {e}")

def close_all_positions():
    """Close all positions"""
    print("\n🔚 CLOSING ALL POSITIONS")
    response = input("   Close all positions? (yes/no): ")
    if response.lower() != 'yes':
        print("   Cancelled")
        return
    try:
        mt4 = get_mt4_prices()
        result = mt4._send({"command": "CLOSE_ALL"})
        if result and result.get('success'):
            print("   ✅ All positions closed")
        else:
            print("   ❌ Failed to close positions")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()