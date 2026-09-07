# test_entry_confirmation.py - IMPROVED VERSION

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_controller2 import ForexTradingController, FOREX_PAIRS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EntryConfirmationTester:
    """Test class for entry confirmation logic with improved S/R checks."""

    def __init__(self):
        config = {
            'pairs': FOREX_PAIRS,
            'min_confidence': 60,
            'cycle_interval': 10,
            'engine_config': {}
        }
        self.controller = ForexTradingController(config)
        
        self.mock_m5_candles = {}
        self.mock_swings = {}
        self.mock_atr = {}
        self.mock_spread = {}

    def setup_mock_data(self, symbol: str, scenario: str):
        """Setup mock data for a specific scenario."""
        base_price = 1.1435
        
        if scenario == 'green_at_support':
            self.mock_m5_candles[symbol] = {'open': base_price - 0.0010, 'close': base_price + 0.0005}
            self.mock_swings[symbol] = {'support': base_price - 0.0030, 'resistance': base_price + 0.0030}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'BUY', 'expected': 'PASS'}
            
        elif scenario == 'green_at_resistance':
            self.mock_m5_candles[symbol] = {'open': base_price - 0.0010, 'close': base_price + 0.0005}
            # Resistance is close to price
            self.mock_swings[symbol] = {'support': base_price - 0.0030, 'resistance': base_price + 0.0005}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'BUY', 'expected': 'FAIL'}
            
        elif scenario == 'red_at_resistance':
            self.mock_m5_candles[symbol] = {'open': base_price + 0.0010, 'close': base_price - 0.0005}
            self.mock_swings[symbol] = {'support': base_price - 0.0030, 'resistance': base_price + 0.0030}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'SELL', 'expected': 'PASS'}
            
        elif scenario == 'red_at_support':
            self.mock_m5_candles[symbol] = {'open': base_price + 0.0010, 'close': base_price - 0.0005}
            # Support is close to price
            self.mock_swings[symbol] = {'support': base_price + 0.0005, 'resistance': base_price + 0.0030}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'SELL', 'expected': 'FAIL'}
            
        elif scenario == 'no_candle_data':
            self.mock_m5_candles[symbol] = None
            self.mock_swings[symbol] = {'support': base_price - 0.0030, 'resistance': base_price + 0.0030}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'BUY', 'expected': 'FAIL'}
            
        elif scenario == 'wide_spread':
            self.mock_m5_candles[symbol] = {'open': base_price - 0.0010, 'close': base_price + 0.0005}
            self.mock_swings[symbol] = {'support': base_price - 0.0030, 'resistance': base_price + 0.0030}
            self.mock_atr[symbol] = 0.0010
            self.mock_spread[symbol] = 0.0050  # 0.5% spread (too wide)
            return {'price': base_price, 'direction': 'BUY', 'expected': 'FAIL'}
            
        elif scenario == 'tight_range':
            # Very narrow range - no room to trade
            self.mock_m5_candles[symbol] = {'open': base_price - 0.0005, 'close': base_price + 0.0005}
            self.mock_swings[symbol] = {'support': base_price - 0.0010, 'resistance': base_price + 0.0010}
            self.mock_atr[symbol] = 0.0005
            self.mock_spread[symbol] = 0.0002
            return {'price': base_price, 'direction': 'BUY', 'expected': 'FAIL'}
        
        return {'price': base_price, 'direction': 'BUY', 'expected': 'UNKNOWN'}

    def run_confirmation(self, symbol: str, scenario: str):
        """Run the confirmation test."""
        test_data = self.setup_mock_data(symbol, scenario)
        price = test_data['price']
        direction = test_data['direction']
        expected = test_data['expected']
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST SCENARIO: {scenario.upper()}")
        print(f"   Symbol: {symbol}")
        print(f"   Direction: {direction}")
        print(f"   Price: {price:.5f}")
        print(f"   Expected Result: {expected}")
        print(f"{'='*60}")
        
        # Show mock data
        print(f"\n📊 MOCK DATA:")
        candle = self.mock_m5_candles.get(symbol)
        if candle:
            is_green = candle['close'] > candle['open']
            print(f"   M5 Candle: {'GREEN' if is_green else 'RED'}")
            print(f"   Open: {candle['open']:.5f} | Close: {candle['close']:.5f}")
        else:
            print(f"   M5 Candle: NO DATA")
        
        swings = self.mock_swings.get(symbol, {})
        print(f"   Support: {swings.get('support', 0):.5f}")
        print(f"   Resistance: {swings.get('resistance', 0):.5f}")
        
        atr = self.mock_atr.get(symbol, 0)
        print(f"   ATR: {atr:.5f}")
        buffer = 0.5 * atr
        print(f"   Buffer (0.5x ATR): {buffer:.5f}")
        
        spread = self.mock_spread.get(symbol, 0.0002)
        spread_pct = spread / price * 100
        print(f"   Spread: {spread_pct:.3f}%")
        
        # Run checks
        print(f"\n🔍 RUNNING CONFIRMATION:")
        
        # 1. Candle check
        if direction == 'BUY':
            candle_ok = candle and candle['close'] > candle['open'] if candle else False
        else:
            candle_ok = candle and candle['close'] < candle['open'] if candle else False
        print(f"   Candle Check: {'✅ PASS' if candle_ok else '❌ FAIL'}")
        
        # 2. Spread check
        spread_ok = spread_pct < 0.02
        print(f"   Spread Check: {'✅ PASS' if spread_ok else '❌ FAIL'}")
        
        # 3. S/R check (STRICT - must be in middle range)
        if swings and atr > 0:
            range_size = swings['resistance'] - swings['support']
            if range_size > 0:
                middle_min = swings['support'] + 0.3 * range_size
                middle_max = swings['resistance'] - 0.3 * range_size
                sr_ok = middle_min < price < middle_max
                print(f"   S/R Check: {'✅ PASS' if sr_ok else '❌ FAIL'}")
                print(f"   Price: {price:.5f} | Range: {middle_min:.5f} - {middle_max:.5f}")
            else:
                sr_ok = False
                print(f"   S/R Check: ❌ FAIL (Invalid range)")
        else:
            sr_ok = False
            print(f"   S/R Check: ❌ FAIL (No S/R data)")
        
        # Final result
        final_ok = candle_ok and spread_ok and sr_ok
        print(f"\n📋 FINAL RESULT: {'✅ PASS' if final_ok else '❌ FAIL'}")
        print(f"   Expected: {expected}")
        print(f"   Match: {'✅' if final_ok == (expected == 'PASS') else '❌'}")
        
        return {
            'scenario': scenario,
            'symbol': symbol,
            'direction': direction,
            'candle_ok': candle_ok,
            'spread_ok': spread_ok,
            'sr_ok': sr_ok,
            'final_ok': final_ok,
            'expected': expected,
            'matched': final_ok == (expected == 'PASS')
        }

    def run_all_tests(self):
        """Run all test scenarios."""
        print("\n" + "="*60)
        print("🏁 STARTING ENTRY CONFIRMATION TESTS (IMPROVED)")
        print("="*60)
        
        scenarios = [
            'green_at_support',
            'green_at_resistance',
            'red_at_resistance',
            'red_at_support',
            'no_candle_data',
            'wide_spread',
            'tight_range'
        ]
        
        results = []
        for scenario in scenarios:
            result = self.run_confirmation('EURUSD', scenario)
            results.append(result)
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results if r['matched'])
        total = len(results)
        
        for r in results:
            status = '✅' if r['matched'] else '❌'
            print(f"   {status} {r['scenario']:25} | Direction: {r['direction']:4} | Expected: {r['expected']:4} | Result: {'PASS' if r['final_ok'] else 'FAIL'}")
        
        print(f"\n   Passed: {passed}/{total} ({passed/total*100:.0f}%)")
        print("="*60)


if __name__ == "__main__":
    tester = EntryConfirmationTester()
    tester.run_all_tests()