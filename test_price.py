# test_forex_prices.py
"""
Diagnostic test to check what prices EA returns for each forex symbol
"""

from mt4_price_provider import get_mt4_prices
import time
import json

mt4 = get_mt4_prices()

# All forex symbols from your MT4 provider
forex_symbols = [
    'EURUSD', 'GBPUSD', 'USDJPY', 'USDCAD', 'AUDUSD', 'NZDUSD', 'USDCHF',
    'EURGBP', 'EURAUD', 'EURCHF', 'EURJPY', 'GBPCHF', 'GBPJPY', 
    'AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'CADJPY', 'CHFJPY', 'NZDJPY'
]

print("=" * 70)
print("FOREX PRICE DIAGNOSTIC TEST")
print("=" * 70)
print(f"Testing {len(forex_symbols)} forex symbols...\n")

results = {}

for symbol in forex_symbols:
    print(f"Requesting {symbol}...", end=" ")
    
    # Direct file communication to avoid any caching
    import os
    cmd_file = mt4.command_file
    resp_file = mt4.response_file
    
    # Clean response file
    if os.path.exists(resp_file):
        try:
            os.remove(resp_file)
        except:
            pass
    
    # Send command
    with open(cmd_file, 'w') as f:
        json.dump({"command": "PRICE", "symbol": symbol}, f)
    
    # Wait for response
    start = time.time()
    response = None
    while time.time() - start < 5:
        if os.path.exists(resp_file):
            with open(resp_file, 'r') as f:
                response = json.load(f)
            os.remove(resp_file)
            break
        time.sleep(0.05)
    
    if response and response.get('success'):
        bid = response.get('bid', 0)
        ask = response.get('ask', 0)
        if isinstance(bid, str):
            bid = float(bid)
        if isinstance(ask, str):
            ask = float(ask)
        
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            results[symbol] = {'success': True, 'price': mid, 'bid': bid, 'ask': ask}
            
            # Determine expected price range (rough sanity check)
            if symbol in ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD']:
                expected_range = (1.0, 1.5) if symbol != 'GBPUSD' else (1.2, 1.5)
                is_plausible = expected_range[0] <= mid <= expected_range[1]
            elif symbol == 'USDJPY':
                is_plausible = 100 <= mid <= 170
            elif symbol in ['USDCAD', 'USDCHF']:
                is_plausible = 0.8 <= mid <= 1.5
            elif 'JPY' in symbol:
                is_plausible = 100 <= mid <= 200
            else:
                is_plausible = 0.5 <= mid <= 2.0
            
            status = "✅" if is_plausible else "⚠️"
            print(f"{status} bid={bid:.5f}, ask={ask:.5f} -> mid={mid:.5f}")
            if not is_plausible:
                print(f"      WARNING: Price seems wrong for {symbol} (expected within {expected_range})")
        else:
            results[symbol] = {'success': False, 'error': 'Zero price'}
            print(f"❌ Zero price")
    else:
        results[symbol] = {'success': False, 'error': 'No response'}
        print(f"❌ No response")
    
    time.sleep(0.5)  # delay between requests

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

working = [s for s, r in results.items() if r.get('success')]
failed = [s for s, r in results.items() if not r.get('success')]
suspicious = [s for s, r in results.items() if r.get('success') and not (
    (s in ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD'] and 1.0 <= r['price'] <= 1.6) or
    (s == 'USDJPY' and 100 <= r['price'] <= 170) or
    (s in ['USDCAD', 'USDCHF'] and 0.8 <= r['price'] <= 1.5) or
    ('JPY' in s and 100 <= r['price'] <= 200) or
    (0.5 <= r['price'] <= 2.0)
)]

print(f"\n✅ Working symbols: {len(working)}")
print(f"❌ Failed symbols: {len(failed)}")
print(f"⚠️ Suspicious prices: {len(suspicious)}")

if suspicious:
    print("\nSuspicious symbols (prices out of expected range):")
    for s in suspicious:
        print(f"   {s}: {results[s]['price']:.5f}")

# Show a few working examples
if working:
    print("\nSample working prices:")
    for s in working[:10]:
        print(f"   {s}: {results[s]['price']:.5f}")