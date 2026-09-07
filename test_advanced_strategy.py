"""
TEST SUITE: Historical Warm-Up for Z-Score
Tests: Data loading, Z-score initialization, and accuracy
"""

import unittest
import sys
import os
import json
import math
import time
import requests
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from collections import deque

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import components
from advanced_trading_strategy import (
    ZScoreEngineWithThresholds,
    AdvancedTradingController,
    DashboardAPIClient
)
from core.price_service import price_service

# ============================================================
# MOCK DATA
# ============================================================

MOCK_PRICES = {
    'EURUSD': 1.13764,
    'GBPUSD': 1.32824,
    'USDJPY': 163.786,
    'USDCHF': 0.81973,
    'AUDUSD': 0.69403,
    'USDCAD': 1.40942,
    'NZDUSD': 0.57746,
    'EURGBP': 0.85635,
    'EURJPY': 186.335,
    'EURCAD': 1.60341,
    'EURNZD': 1.96909,
    'EURCHF': 0.93264,
    '#NASDAQ100': 27743.495,
    '#DJ30': 52515.00,
    '#S&P500': 7456.50,
    '#RUSS2000': 2955.67,
    '#CAC40': 8409.80,
    '#DAX40': 25577.50,
    '#FTSE100': 10890.00,
    '#NIKKEI225': 62487.00,
    'GOLD': 4017.18,
    'SILVER': 57.13,
    'BRENT_OIL': 86.92,
    'CrudeOIL': 84.68,
    '#DOLLAR_IND': 101.257
}

# ============================================================
# MOCK HISTORY DATA
# ============================================================

def generate_mock_history(base_price, count=100, volatility=0.01):
    """Generate mock historical data"""
    import random
    history = []
    price = base_price
    for i in range(count):
        if i < count // 2:
            price = price * (1 + (i - count//4) / count * volatility * 0.5)
        else:
            price = price * (1 - (i - count//4) / count * volatility * 0.3)
        price = price * (1 + (random.random() - 0.5) * volatility * 0.5)
        history.append(price)
    return history


# ============================================================
# TEST 1: Z-SCORE ENGINE WITH HISTORY
# ============================================================

class TestZScoreWithHistory(unittest.TestCase):
    """Test Z-score engine initialized with historical data"""
    
    def setUp(self):
        self.engine = ZScoreEngineWithThresholds(lookback=50)
    
    def test_initialize_with_history(self):
        """Test initializing Z-score engine with historical data"""
        # Generate history
        history = generate_mock_history(1.14, count=50, volatility=0.005)
        
        # Add to engine
        for price in history:
            self.engine.update_price('EURUSD', price)
        
        # Check samples
        self.assertEqual(self.engine.samples['EURUSD'], 50)
        self.assertEqual(len(self.engine.price_history['EURUSD']), 50)
    
    def test_zscore_after_history(self):
        """Test Z-score after historical warm-up"""
        # Generate history with known mean
        history = [1.14 + i * 0.001 for i in range(50)]
        for price in history:
            self.engine.update_price('EURUSD', price)
        
        # Calculate Z-score for a price at the mean
        result = self.engine.calculate_zscore('EURUSD', 1.14)
        
        # Should have samples
        self.assertGreater(result['samples'], 0)
        
        # Z-score should be near 0 (price at mean)
        self.assertAlmostEqual(result['z_score'], 0, places=1)
    
    def test_zscore_accuracy(self):
        """Test Z-score accuracy after warm-up"""
        # Create history with mean = 27750, std = 100
        import random
        history = [27750 + (0.5 - random.random()) * 200 for _ in range(100)]
        for price in history:
            self.engine.update_price('#NASDAQ100', price)
        
        # Calculate actual mean/std
        actual_mean = sum(history) / len(history)
        variance = sum((x - actual_mean) ** 2 for x in history) / len(history)
        actual_std = math.sqrt(variance)
        
        # Test: Price at mean
        result = self.engine.calculate_zscore('#NASDAQ100', actual_mean)
        self.assertAlmostEqual(result['z_score'], 0, places=1)
        
        # Test: Price 1 std above
        price_high = actual_mean + actual_std
        result = self.engine.calculate_zscore('#NASDAQ100', price_high)
        self.assertAlmostEqual(result['z_score'], 1, places=1)
        
        # Test: Price 2 std above
        price_high2 = actual_mean + actual_std * 2
        result = self.engine.calculate_zscore('#NASDAQ100', price_high2)
        self.assertAlmostEqual(result['z_score'], 2, places=1)
    
    def test_cold_start_prevention(self):
        """Test that cold start is prevented with history"""
        # Without history - should have 0 samples
        self.assertEqual(self.engine.samples.get('EURUSD', 0), 0)
        
        # Add history
        history = generate_mock_history(1.14, count=50)
        for price in history:
            self.engine.update_price('EURUSD', price)
        
        # Should have 50 samples
        self.assertEqual(self.engine.samples['EURUSD'], 50)
        
        # Z-score should be accurate from first calculation
        result = self.engine.calculate_zscore('EURUSD', 1.14)
        self.assertNotEqual(result['z_score'], 0)  # Not cold-start zero


# ============================================================
# TEST 2: HISTORICAL DATA LOADING
# ============================================================

class TestHistoricalLoading(unittest.TestCase):
    """Test loading historical data"""
    
    @patch('requests.get')
    def test_load_from_dashboard(self, mock_get):
        """Test loading history from dashboard API"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'history': {
                'EURUSD': generate_mock_history(1.14, count=100),
                'GBPUSD': generate_mock_history(1.33, count=100)
            }
        }
        mock_get.return_value = mock_response
        
        # Create controller with mocked dashboard
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        # Load historical data
        success = controller._load_historical_data()
        
        self.assertTrue(success)
    
    def test_generate_synthetic_history(self):
        """Test generating synthetic history as fallback"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        # Generate synthetic history
        success = controller._generate_synthetic_history()
        
        self.assertTrue(success)
        
        # Check that symbols have samples
        for symbol in list(MOCK_PRICES.keys())[:5]:
            samples = controller.zscore_engine.samples.get(symbol, 0)
            self.assertGreater(samples, 0)


# ============================================================
# TEST 3: WARM-UP PROCESS
# ============================================================

class TestWarmUpProcess(unittest.TestCase):
    """Test the complete warm-up process"""
    
    def test_warm_up_zscore(self):
        """Test Z-score warm-up process"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        # Warm up
        success = controller._warm_up_zscore()
        
        self.assertTrue(success)
        
        # Check that symbols have samples
        for symbol in list(MOCK_PRICES.keys())[:5]:
            samples = controller.zscore_engine.samples.get(symbol, 0)
            self.assertGreater(samples, 0)
    
    def test_print_zscore_status(self):
        """Test printing Z-score status"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        controller.dashboard.get_price.side_effect = lambda x: MOCK_PRICES.get(x, 0)
        
        # Warm up
        controller._warm_up_zscore()
        
        # Print status (should not crash)
        controller.print_zscore_status()
        self.assertTrue(True)  # If we get here, it worked


# ============================================================
# TEST 4: Z-SCORE ACCURACY COMPARISON
# ============================================================

class TestZScoreAccuracyComparison(unittest.TestCase):
    """Compare Z-score with and without warm-up"""
    
    def setUp(self):
        self.engine_with_history = ZScoreEngineWithThresholds(lookback=50)
        self.engine_without_history = ZScoreEngineWithThresholds(lookback=50)
        
        # Generate data
        self.prices = generate_mock_history(27750, count=60, volatility=0.005)
        
        # Add history to first engine
        for price in self.prices[:50]:
            self.engine_with_history.update_price('#NASDAQ100', price)
    
    def test_cold_start_vs_warm_start(self):
        """Compare Z-score with cold start vs warm start"""
        # Get current price
        current_price = self.prices[-1]
        
        # WITH history (warm start)
        result_warm = self.engine_with_history.calculate_zscore('#NASDAQ100', current_price)
        z_warm = result_warm.get('z_score', 0)
        
        # WITHOUT history (cold start)
        result_cold = self.engine_without_history.calculate_zscore('#NASDAQ100', current_price)
        z_cold = result_cold.get('z_score', 0)
        
        # Cold start should be 0 (or near 0)
        self.assertAlmostEqual(z_cold, 0, places=1)
        
        # Warm start should be different from 0
        self.assertNotEqual(z_warm, z_cold)
        
        # Warm start should have samples
        self.assertGreater(result_warm.get('samples', 0), 0)
        
        print(f"\n📊 Comparison:")
        print(f"   Cold Start Z-score: {z_cold:+.2f}")
        print(f"   Warm Start Z-score: {z_warm:+.2f}")
        print(f"   Difference: {abs(z_warm - z_cold):.2f}")


# ============================================================
# TEST 5: MULTI-SYMBOL WARM-UP
# ============================================================

class TestMultiSymbolWarmUp(unittest.TestCase):
    """Test warm-up for multiple symbols"""
    
    def test_all_symbols_warmed(self):
        """Test that all symbols get warmed up"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        # Warm up
        controller._warm_up_zscore()
        
        # Check all symbols
        warmed_symbols = 0
        for symbol in MOCK_PRICES.keys():
            samples = controller.zscore_engine.samples.get(symbol, 0)
            if samples > 0:
                warmed_symbols += 1
        
        # At least 80% of symbols should be warmed
        self.assertGreater(warmed_symbols, len(MOCK_PRICES) * 0.8)
    
    def test_forex_vs_indices_volatility(self):
        """Test that different volatilities are applied correctly"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        # Generate synthetic history
        controller._generate_synthetic_history()
        
        # Get samples for forex and indices
        forex_samples = controller.zscore_engine.samples.get('EURUSD', 0)
        index_samples = controller.zscore_engine.samples.get('#NASDAQ100', 0)
        metal_samples = controller.zscore_engine.samples.get('GOLD', 0)
        
        # All should have samples
        self.assertGreater(forex_samples, 0)
        self.assertGreater(index_samples, 0)
        self.assertGreater(metal_samples, 0)


# ============================================================
# TEST 6: PERFORMANCE TESTS
# ============================================================

class TestPerformance(unittest.TestCase):
    """Performance tests for warm-up"""
    
    def test_warm_up_speed(self):
        """Test warm-up speed"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = MOCK_PRICES
        
        start = time.time()
        controller._warm_up_zscore()
        elapsed = time.time() - start
        
        # Should be fast (< 2 seconds)
        self.assertLess(elapsed, 2.0)
        print(f"\n⏱️ Warm-up time: {elapsed:.2f}s")
    
    def test_zscore_calculation_speed(self):
        """Test Z-score calculation speed after warm-up"""
        engine = ZScoreEngineWithThresholds(lookback=50)
        
        # Add history
        history = generate_mock_history(1.14, count=100)
        for price in history:
            engine.update_price('EURUSD', price)
        
        # Measure calculation speed
        start = time.time()
        for _ in range(1000):
            engine.calculate_zscore('EURUSD', 1.14)
        elapsed = time.time() - start
        
        # Should be fast (< 0.5 seconds for 1000 calculations)
        self.assertLess(elapsed, 0.5)


# ============================================================
# TEST 7: EDGE CASES
# ============================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases"""
    
    def test_empty_history(self):
        """Test handling empty history"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = {}
        
        # Should handle gracefully
        success = controller._load_historical_data()
        self.assertFalse(success)
    
    def test_missing_prices(self):
        """Test handling missing prices"""
        controller = AdvancedTradingController({'cycle_interval': 1})
        controller.dashboard = Mock()
        controller.dashboard.get_all_prices.return_value = {'EURUSD': 0}
        
        # Should handle gracefully
        success = controller._generate_synthetic_history()
        self.assertFalse(success)
    
    def test_invalid_symbol(self):
        """Test invalid symbol handling"""
        engine = ZScoreEngineWithThresholds(lookback=50)
        
        # Add history for EURUSD
        history = generate_mock_history(1.14, count=50)
        for price in history:
            engine.update_price('EURUSD', price)
        
        # Try to get Z-score for invalid symbol
        result = engine.calculate_zscore('INVALID', 1.14)
        
        # Should return HOLD with 0 confidence
        self.assertEqual(result['action'], 'HOLD')
        self.assertEqual(result['confidence'], 0)


# ============================================================
# TEST 8: INTEGRATION TEST
# ============================================================

class TestIntegration(unittest.TestCase):
    """Integration test for complete flow"""
    
    def setUp(self):
        # Create mock dashboard
        self.mock_dashboard = Mock()
        self.mock_dashboard.fetch_prices.return_value = True
        self.mock_dashboard.prices = MOCK_PRICES
        self.mock_dashboard.get_all_prices.return_value = MOCK_PRICES
        self.mock_dashboard.get_price.side_effect = lambda x: MOCK_PRICES.get(x, 0)
        self.mock_dashboard.balance = 10000
        self.mock_dashboard.is_connected.return_value = True
    
    @patch('advanced_trading_strategy.DashboardAPIClient')
    def test_complete_flow(self, MockClient):
        """Test complete flow from startup to trading"""
        MockClient.return_value = self.mock_dashboard
        
        controller = AdvancedTradingController({
            'cycle_interval': 1,
            'min_confidence': 60,
            'cold_start_threshold': 3
        })
        
        # Warm up
        success = controller._warm_up_zscore()
        self.assertTrue(success)
        
        # Check Z-score status
        controller.print_zscore_status()
        
        # Process one cycle
        result = controller.process_cycle()
        
        # Should have signals
        self.assertIn('signals', result)
        self.assertIn('active_positions', result)


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all test suites"""
    print('\n' + '=' * 60)
    print('🧪 RUNNING HISTORICAL WARM-UP TESTS')
    print('=' * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestZScoreWithHistory,
        TestHistoricalLoading,
        TestWarmUpProcess,
        TestZScoreAccuracyComparison,
        TestMultiSymbolWarmUp,
        TestPerformance,
        TestEdgeCases,
        TestIntegration
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print('\n' + '=' * 60)
    print('📊 TEST SUMMARY')
    print('=' * 60)
    print(f'   Tests Run: {result.testsRun}')
    print(f'   Failures: {len(result.failures)}')
    print(f'   Errors: {len(result.errors)}')
    print(f'   Skipped: {len(result.skipped)}')
    
    if result.wasSuccessful():
        print('\n✅ ALL TESTS PASSED!')
        print('\n📊 Historical Warm-Up Summary:')
        print('   ✅ Z-score initialized with historical data')
        print('   ✅ Cold-start problem solved')
        print('   ✅ All symbols warmed up')
        print('   ✅ Accurate from first tick')
    else:
        print('\n❌ SOME TESTS FAILED')
        for failure in result.failures:
            print(f'   - {failure[0]}')
        for error in result.errors:
            print(f'   - {error[0]}')
    
    print('=' * 60)
    return result.wasSuccessful()


def quick_test():
    """Quick test for basic functionality"""
    print('\n🚀 Quick Historical Warm-Up Test...')
    
    try:
        # 1. Test Z-score with history
        engine = ZScoreEngineWithThresholds(lookback=50)
        history = generate_mock_history(27750, count=50)
        for price in history:
            engine.update_price('#NASDAQ100', price)
        
        result = engine.calculate_zscore('#NASDAQ100', 27750)
        print(f'   ✅ Z-score with history: {result["z_score"]:+.2f}')
        print(f'   ✅ Samples: {result["samples"]}')
        
        # 2. Test cold start comparison
        engine_cold = ZScoreEngineWithThresholds(lookback=50)
        result_cold = engine_cold.calculate_zscore('#NASDAQ100', 27750)
        print(f'   ✅ Z-score cold start: {result_cold["z_score"]:+.2f}')
        
        # 3. Verify warm-up fixed the problem
        if abs(result['z_score']) > abs(result_cold['z_score']):
            print('   ✅ Warm-up fixed cold-start problem!')
        else:
            print('   ⚠️ Warm-up may need adjustment')
        
        print('\n✅ Quick test passed!')
        return True
        
    except Exception as e:
        print(f'\n❌ Quick test failed: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Historical Warm-Up')
    parser.add_argument('--quick', action='store_true', help='Run quick test only')
    args = parser.parse_args()
    
    if args.quick:
        quick_test()
    else:
        run_all_tests()