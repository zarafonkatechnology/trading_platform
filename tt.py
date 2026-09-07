# test_trading_controller_ime.py
"""
Test script for Trading Controller - Indices, Metals & Energy
"""

import sys
import os
import time
from datetime import datetime

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("🧪 TESTING TRADING CONTROLLER - INDICES, METALS & ENERGY")
print("=" * 70)
print()

# ============================================================
# TEST 1: Import and Initialize
# ============================================================

print("[1] Importing Trading Controller...")
try:
    from trading_controller import AITradingController, SYMBOLS_TO_TRADE, SYMBOL_CONFIG
    print("   ✅ Trading Controller imported successfully")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

print()

# ============================================================
# TEST 2: Initialize Controller
# ============================================================

print("[2] Initializing Trading Controller...")
try:
    controller = AITradingController()
    print("   ✅ Trading Controller initialized")
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# ============================================================
# TEST 3: Check Symbols
# ============================================================

print("[3] Checking Symbols...")
print(f"   📊 Total Symbols: {len(SYMBOLS_TO_TRADE)}")
print("\n   📋 Symbols:")
for symbol in SYMBOLS_TO_TRADE:
    config = SYMBOL_CONFIG.get(symbol, {})
    print(f"      {symbol:<15} | {config.get('type', 'unknown'):<10} | {config.get('volume', 0.02)} lots")

print()

# ============================================================
# TEST 4: Get Prices
# ============================================================

print("[4] Getting Prices from Dashboard...")
try:
    from trading_controller import get_price_from_dashboard
    
    prices_found = 0
    for symbol in SYMBOLS_TO_TRADE[:5]:  # Test first 5 symbols
        price = get_price_from_dashboard(symbol)
        if price > 0:
            print(f"   ✅ {symbol}: {price:.2f}")
            prices_found += 1
        else:
            print(f"   ❌ {symbol}: NO PRICE")
    
    print(f"\n   📊 Prices found: {prices_found}/5")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ============================================================
# TEST 5: Test get_correct_price
# ============================================================

print("[5] Testing get_correct_price...")
try:
    test_symbols = ['GOLD', '#NASDAQ100', 'BRENT_OIL', 'SILVER', '#S&P500']
    for symbol in test_symbols:
        price = controller.get_correct_price(symbol)
        if price > 0:
            print(f"   ✅ {symbol}: {price:.2f}")
        else:
            print(f"   ❌ {symbol}: NO PRICE")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ============================================================
# TEST 6: Test analyze_market
# ============================================================

print("[6] Testing analyze_market...")
try:
    test_symbols = ['GOLD', '#NASDAQ100', 'BRENT_OIL']
    for symbol in test_symbols:
        result = controller.analyze_market(symbol)
        action = result.get('action', 'HOLD')
        confidence = result.get('confidence', 0)
        z_score = result.get('z_score', 0)
        price = result.get('price', 0)
        
        print(f"   📊 {symbol}:")
        print(f"      Price: {price:.2f}")
        print(f"      Z-Score: {z_score:.2f}")
        print(f"      Action: {action} ({confidence:.0f}%)")
        print(f"      Reasoning: {result.get('reasoning', 'N/A')}")
        print()
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# ============================================================
# TEST 7: Test Place Order (Simulated)
# ============================================================

print("[7] Testing place_order (simulated)...")
try:
    test_symbol = 'GOLD'
    print(f"   📊 Testing {test_symbol} BUY order...")
    success, message = controller.place_order(test_symbol, 'BUY')
    if success:
        print(f"   ✅ {message}")
        print(f"   📊 Active positions: {len(controller.active_positions)}")
    else:
        print(f"   ❌ {message}")
    
    # Clear position
    if test_symbol in controller.active_positions:
        del controller.active_positions[test_symbol]
        print(f"   🗑️ Cleared test position")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ============================================================
# TEST 8: Test Run Cycle (Quick)
# ============================================================

print("[8] Testing run_cycle (quick)...")
try:
    # Run one cycle quickly
    print("   ⏳ Running cycle...")
    controller.run_cycle()
    print("   ✅ Cycle complete")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ============================================================
# TEST 9: Test Start/Stop
# ============================================================

print("[9] Testing start/stop...")
try:
    print("   Starting controller...")
    controller.start()
    time.sleep(2)
    
    # Get status
    status = controller.get_status()
    print(f"   📊 Status: Running={status.get('running', False)}")
    print(f"   📊 Active positions: {len(status.get('positions', {}))}")
    
    print("   Stopping controller...")
    controller.stop()
    print("   ✅ Stop complete")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# ============================================================
# TEST 10: Quick Cycle with 2 Symbols
# ============================================================

print("[10] Running quick cycle with 2 symbols...")
try:
    # Temporarily reduce symbols for quick test
    original_symbols = controller.symbols
    controller.symbols = ['GOLD', '#NASDAQ100']
    
    print("   ⏳ Running cycle on GOLD and NASDAQ100...")
    controller.run_cycle()
    
    # Restore symbols
    controller.symbols = original_symbols
    print("   ✅ Quick cycle complete")
except Exception as e:
    print(f"   ❌ Error: {e}")
    controller.symbols = original_symbols

print()

# ============================================================
# SUMMARY
# ============================================================

print("=" * 70)
print("✅ TEST COMPLETE")
print("=" * 70)
print()
print("📋 SUMMARY:")
print(f"   - Symbols: {len(SYMBOLS_TO_TRADE)}")
print(f"   - Metals: {len([s for s in SYMBOLS_TO_TRADE if SYMBOL_CONFIG.get(s, {}).get('type') == 'metal'])}")
print(f"   - Indices: {len([s for s in SYMBOLS_TO_TRADE if SYMBOL_CONFIG.get(s, {}).get('type') == 'index'])}")
print(f"   - Energy: {len([s for s in SYMBOLS_TO_TRADE if SYMBOL_CONFIG.get(s, {}).get('type') == 'energy'])}")
print()
print("📊 INSTRUMENTS TRADED:")
print("   METALS:")
for s in SYMBOLS_TO_TRADE:
    if SYMBOL_CONFIG.get(s, {}).get('type') == 'metal':
        print(f"      - {s}")
print("   INDICES:")
for s in SYMBOLS_TO_TRADE:
    if SYMBOL_CONFIG.get(s, {}).get('type') == 'index':
        print(f"      - {s}")
print("   ENERGY:")
for s in SYMBOLS_TO_TRADE:
    if SYMBOL_CONFIG.get(s, {}).get('type') == 'energy':
        print(f"      - {s}")
print()
print("=" * 70)