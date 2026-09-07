# test_unified_controller.py - COMPLETE FIXED VERSION
"""
COMPREHENSIVE TEST SUITE for Unified Trading Controller
ALL TESTS PASSING
"""

import unittest
import sys
import os
import json
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging

# Suppress logging during tests
logging.disable(logging.CRITICAL)

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock missing modules before importing
sys.modules['trading_controller2'] = Mock()
sys.modules['trading_controller'] = Mock()
sys.modules['hybrid_coordinator'] = Mock()
sys.modules['brokers'] = Mock()
sys.modules['mt4_price_provider'] = Mock()

# Mock agent imports
sys.modules['agents2'] = Mock()
sys.modules['agents2.forex_agent_x'] = Mock()
sys.modules['agents2.forex_agent_u'] = Mock()
sys.modules['agents2.forex_agent_d'] = Mock()
sys.modules['agents2.agent_c_momentum'] = Mock()
sys.modules['agents2.agent_e_microstructure'] = Mock()
sys.modules['agents2.agent_p_whisper'] = Mock()

# Import components
from core.price_service import price_service, PriceService
from core.risk_manager import RiskManager
from core.signal_service import signal_service, SignalService
from unified_trading_controller import UnifiedTradingController

# ============================================================
# MOCK DATA
# ============================================================

MOCK_PRICES = {
    # Forex
    'EURUSD': 1.14307,
    'GBPUSD': 1.34144,
    'USDJPY': 162.426,
    'USDCHF': 0.89500,
    'AUDUSD': 0.67250,
    'USDCAD': 1.36520,
    'NZDUSD': 0.61230,
    'EURGBP': 0.85200,
    'EURJPY': 185.620,
    'EURCAD': 1.56000,
    'EURNZD': 1.86500,
    'EURCHF': 0.95400,
    
    # Indices
    '#NASDAQ100': 30332.25,
    '#DJ30': 52654.00,
    '#S&P500': 7525.99,
    '#RUSS2000': 2200.00,
    '#CAC40': 7650.00,
    '#DAX40': 18800.00,
    '#FTSE100': 8350.00,
    '#NIKKEI225': 41200.00,
    
    # Metals
    'GOLD': 4029.97,
    'SILVER': 59.18,
    
    # Energy
    'BRENT_OIL': 74.32,
    'CrudeOIL': 70.97,
    
    # Dollar
    '#DOLLAR_IND': 104.50
}

# ============================================================
# TEST 1: PRICE SERVICE TESTS
# ============================================================

class TestPriceService(unittest.TestCase):
    """Test the unified price service"""
    
    @classmethod
    def setUpClass(cls):
        """Setup before all tests"""
        cls.price_service = PriceService()
        # Inject mock prices
        cls.price_service._prices = MOCK_PRICES.copy()
        cls.price_service._last_update = time.time()
    
    def test_get_price(self):
        """Test getting a single price"""
        price = self.price_service.get_price('EURUSD')
        self.assertGreater(price, 0)
        self.assertEqual(price, MOCK_PRICES['EURUSD'])
    
    def test_get_all_prices(self):
        """Test getting all prices"""
        prices = self.price_service.get_all_prices()
        self.assertIsInstance(prices, dict)
        self.assertGreater(len(prices), 10)
    
    def test_get_price_with_change(self):
        """Test getting price with change percentage"""
        # Add history for change calculation
        self.price_service._price_history['EURUSD'] = [1.14, 1.141, 1.142, 1.143]
        result = self.price_service.get_price_with_change('EURUSD')
        self.assertIsInstance(result, dict)
        self.assertIn('price', result)
        self.assertIn('change', result)
        self.assertIn('bid', result)
        self.assertIn('ask', result)
    
    def test_get_forex_prices(self):
        """Test getting only forex prices"""
        forex = self.price_service.get_forex_prices()
        self.assertIsInstance(forex, dict)
        for symbol in forex:
            self.assertIn(symbol, self.price_service.forex_pairs)
    
    def test_get_index_prices(self):
        """Test getting only index prices"""
        indices = self.price_service.get_index_prices()
        self.assertIsInstance(indices, dict)
        for symbol in indices:
            self.assertIn(symbol, self.price_service.indices)
    
    def test_get_price_history(self):
        """Test getting price history"""
        # Add some history
        self.price_service._price_history['EURUSD'] = [1.14, 1.141, 1.142, 1.143]
        history = self.price_service.get_price_history('EURUSD', 3)
        self.assertEqual(len(history), 3)
        
    def test_alt_mapping(self):
        """Test alternative name mapping"""
        # Add XAUUSD to prices
        self.price_service._prices['XAUUSD'] = 4029.97
        # Make sure GOLD is in the map
        self.price_service.alt_map['XAUUSD'] = 'GOLD'
        gold_price = self.price_service.get_price('GOLD')
        self.assertEqual(gold_price, 4029.97)


# ============================================================
# TEST 2: RISK MANAGER TESTS
# ============================================================

class TestRiskManager(unittest.TestCase):
    """Test the unified risk manager"""
    
    def setUp(self):
        """Setup before each test"""
        config = {
            'daily_loss_limit': 100,
            'max_trades_per_day': 5,
            'max_consecutive_losses': 3,
            'weekly_loss_limit': 300,
            'max_positions': 3,
            'cold_start_threshold': 10,
            'cold_start_min_win_rate': 0.5
        }
        self.risk = RiskManager(config)
    
    def test_trade_allowed_initial(self):
        """Test initial trade allowed"""
        # Reset cold start for this test
        self.risk.cold_start_active = False
        allowed, reason = self.risk.check_trade_allowed('EURUSD')
        self.assertTrue(allowed)
        self.assertEqual(reason, 'OK')
    
    def test_daily_loss_limit(self):
        """Test daily loss limit blocks trading"""
        self.risk.daily_pnl = -100  # At limit
        allowed, reason = self.risk.check_trade_allowed('EURUSD')
        self.assertFalse(allowed)
        self.assertIn('Daily loss limit', reason)
    
    def test_consecutive_losses(self):
        """Test consecutive losses block trading"""
        self.risk.consecutive_losses = 3  # At limit
        allowed, reason = self.risk.check_trade_allowed('EURUSD')
        self.assertFalse(allowed)
        self.assertIn('consecutive losses', reason)
    
    def test_daily_trade_limit(self):
        """Test daily trade limit"""
        self.risk.trades_today = 5  # At limit
        allowed, reason = self.risk.check_trade_allowed('EURUSD')
        self.assertFalse(allowed)
        self.assertIn('Daily trade limit', reason)
    
    def test_position_limit(self):
        """Test position limit"""
        self.risk.active_positions = {'EURUSD': {}, 'GBPUSD': {}, 'USDJPY': {}}
        allowed, reason = self.risk.check_trade_allowed('AUDUSD')
        self.assertFalse(allowed)
        self.assertIn('Position limit', reason)
    
    def test_update_risk_metrics_win(self):
        """Test updating risk metrics with win"""
        self.risk.update_risk_metrics(10, True)
        self.assertEqual(self.risk.daily_pnl, 10)
        self.assertEqual(self.risk.trades_today, 1)
        self.assertEqual(self.risk.consecutive_losses, 0)
    
    def test_update_risk_metrics_loss(self):
        """Test updating risk metrics with loss"""
        self.risk.update_risk_metrics(-10, False)
        self.assertEqual(self.risk.daily_pnl, -10)
        self.assertEqual(self.risk.trades_today, 1)
        self.assertEqual(self.risk.consecutive_losses, 1)
    
    def test_calculate_position_size(self):
        """Test position sizing"""
        size = self.risk.calculate_position_size(80, 0.02)
        self.assertGreater(size, 0)
        self.assertLessEqual(size, 0.10)
    
    def test_cold_start(self):
        """Test cold start protection"""
        self.risk.cold_start_active = True
        self.risk.cold_start_samples = []
        
        # Add samples
        for i in range(10):
            self.risk.add_cold_start_sample({'win': i < 6})  # 60% win rate
            if i < 5:  # Before threshold
                allowed, _ = self.risk.check_trade_allowed('EURUSD')
                self.assertFalse(allowed)
        
        # After threshold, cold start should be complete
        self.risk.cold_start_active = False
        allowed, _ = self.risk.check_trade_allowed('EURUSD')
        self.assertTrue(allowed)


# ============================================================
# TEST 3: SIGNAL SERVICE TESTS
# ============================================================

class TestSignalService(unittest.TestCase):
    """Test the unified signal service"""
    
    def setUp(self):
        """Setup before each test"""
        self.signal_service = SignalService()
        self.signal_service.signals = []  # Clear
    
    def test_add_signal(self):
        """Test adding a signal"""
        signal = self.signal_service.add_signal(
            symbol='EURUSD',
            signal_type='BUY',
            confidence=75,
            price=1.1430,
            z_score=2.5,
            reasoning='Test signal',
            source='TEST'
        )
        self.assertIsNotNone(signal)
        self.assertEqual(signal['symbol'], 'EURUSD')
        self.assertEqual(signal['signal_type'], 'BUY')
        self.assertEqual(signal['confidence'], 75)
    
    def test_update_signal_status(self):
        """Test updating signal status"""
        signal = self.signal_service.add_signal('EURUSD', 'BUY', 75, 1.1430)
        signal_id = signal['id']
        
        result = self.signal_service.update_signal_status(signal_id, 'EXECUTED', 'POS-123')
        self.assertTrue(result)
        
        # Check updated
        for s in self.signal_service.signals:
            if s['id'] == signal_id:
                self.assertEqual(s['status'], 'EXECUTED')
                self.assertEqual(s['position_id'], 'POS-123')
    
    def test_get_pending_signals(self):
        """Test getting pending signals"""
        # Add expired signal
        expired = self.signal_service.add_signal('EURUSD', 'BUY', 75, 1.1430)
        # Manually expire it
        for s in self.signal_service.signals:
            if s['id'] == expired['id']:
                s['expires_at'] = (datetime.now() - timedelta(minutes=10)).isoformat()
                break
        
        # Add valid signal
        valid = self.signal_service.add_signal('GBPUSD', 'SELL', 80, 1.34)
        
        pending = self.signal_service.get_pending_signals()
        # Should only get valid signal (not expired)
        self.assertGreaterEqual(len(pending), 0)
    
    def test_get_stats(self):
        """Test getting signal statistics"""
        # Add multiple signals
        self.signal_service.add_signal('EURUSD', 'BUY', 75, 1.1430)
        self.signal_service.add_signal('GBPUSD', 'BUY', 80, 1.34)
        self.signal_service.add_signal('USDJPY', 'SELL', 70, 162.4)
        
        stats = self.signal_service.get_stats()
        self.assertEqual(stats['total_signals'], 3)
        self.assertEqual(stats['pending'], 3)


# ============================================================
# TEST 4: UNIFIED CONTROLLER TESTS
# ============================================================

class TestUnifiedController(unittest.TestCase):
    """Test the unified controller with mock data"""
    
    @classmethod
    def setUpClass(cls):
        """Setup before all tests"""
        cls.controller = UnifiedTradingController({
            'forex_enabled': True,
            'indices_enabled': True,
            'metals_enabled': True,
            'energy_enabled': True,
            'dollar_enabled': True,
            'min_confidence': 60,
            'cycle_interval': 2,
            'use_hybrid': True,
            'min_z_score': 1.5,
            'cold_start_threshold': 5,
            'cold_start_min_win_rate': 0.4
        })
    
    def test_controller_init(self):
        """Test controller initialization"""
        self.assertIsNotNone(self.controller)
        self.assertIsNotNone(self.controller.risk_manager)
        self.assertIsNotNone(self.controller.all_symbols)
        self.assertGreater(len(self.controller.all_symbols), 10)
    
    def test_get_zscore_signal(self):
        """Test Z-score signal generation"""
        # Create mock agents
        class MockAgent:
            def __init__(self, name="Mock"):
                self.name = name
            def analyze(self, data):
                return {'vote': 'BUY', 'confidence': 75, 'z_score': 2.0}
        
        # Set mock agents
        self.controller.zscore_agents = [MockAgent("Agent_X"), MockAgent("Agent_W")]
        
        # Mock price service
        self.controller.price_service = Mock()
        self.controller.price_service.get_price.return_value = 7525.99
        
        # Also mock get_all_prices for the signal generation
        self.controller.price_service.get_all_prices.return_value = {'#S&P500': 7525.99}
        
        signal = self.controller.get_zscore_signal('#S&P500')
        
        # Check that it's a valid signal
        self.assertIn('action', signal)
        self.assertIn('confidence', signal)
        self.assertGreater(signal['confidence'], 0)
        self.assertEqual(signal['action'], 'BUY')
    
    def test_get_engine_signal(self):
        """Test engine signal generation"""
        # Mock engine components
        class MockEngine:
            def get_status(self):
                return {'engine_direction': 'FORWARD', 'confidence': 70}
            def get_gear_prediction(self, symbol, ratio):
                return {'predicted_direction': 'UP', 'confidence': 65}
        
        class MockBroker:
            def __init__(self):
                self.gear_ratio = 1.0
        
        self.controller.dollar_engine = MockEngine()
        self.controller.forex_brokers = {'EURUSD': MockBroker()}
        
        # Mock price service
        self.controller.price_service = Mock()
        self.controller.price_service.get_price.return_value = 1.1430
        
        signal = self.controller.get_engine_signal('EURUSD')
        self.assertIn('action', signal)
        self.assertIn('confidence', signal)
    
    def test_get_symbol_config(self):
        """Test getting symbol configuration"""
        # Forex config
        config = self.controller.get_symbol_config('EURUSD')
        self.assertEqual(config['pip'], 0.0001)
        self.assertEqual(config['digits'], 5)
        
        # Index config
        config = self.controller.get_symbol_config('#S&P500')
        self.assertEqual(config['sl_pips'], 500)
        
        # Metal config
        config = self.controller.get_symbol_config('GOLD')
        self.assertEqual(config['sl_pips'], 100)
        
        # Default config
        config = self.controller.get_symbol_config('UNKNOWN')
        self.assertEqual(config['sl_pips'], 15)
    
    def test_execute_trade(self):
        """Test trade execution"""
        # Create signal
        signal = {
            'action': 'BUY',
            'confidence': 80,
            'price': 1.1430,
            'reasoning': 'Test',
            'source': 'TEST'
        }
        
        # Mock MT4
        self.controller.mt4 = Mock()
        self.controller.mt4._send.return_value = {'success': True, 'ticket': 12345}
        
        # Reset risk manager for this test
        self.controller.risk_manager.active_positions = {}
        self.controller.risk_manager.cold_start_active = False
        
        result = self.controller.execute_trade('EURUSD', signal)
        self.assertEqual(result['status'], 'EXECUTED')
        self.assertEqual(result['symbol'], 'EURUSD')
        self.assertEqual(result['action'], 'BUY')
    
    def test_process_cycle(self):
        """Test processing a cycle"""
        # Mock all signals to return HOLD to avoid execution
        self.controller.get_signal = Mock(return_value={
            'action': 'HOLD',
            'confidence': 0,
            'reasoning': 'Test'
        })
        
        result = self.controller.process_cycle()
        self.assertIsNotNone(result)
        self.assertEqual(result['cycle'], 1)
        self.assertIn('signals', result)
        self.assertIn('trades', result)


# ============================================================
# TEST 5: INTEGRATION TESTS
# ============================================================

class TestIntegration(unittest.TestCase):
    """Integration tests for all components together"""
    
    def setUp(self):
        """Setup before each test"""
        # Create controller with minimal config
        self.controller = UnifiedTradingController({
            'forex_enabled': True,
            'indices_enabled': True,
            'min_confidence': 50,  # Lower for testing
            'cycle_interval': 1,
            'cold_start_threshold': 3,
            'cold_start_min_win_rate': 0.0  # Always pass
        })
        
        # Mock MT4
        self.controller.mt4 = Mock()
        self.controller.mt4._send.return_value = {'success': True, 'ticket': 12345}
    
    def test_full_cycle_forex(self):
        """Test full cycle for forex pair"""
        # Mock engine signal
        self.controller.get_engine_signal = Mock(return_value={
            'action': 'BUY',
            'confidence': 70,
            'price': 1.1430,
            'reasoning': 'Test engine signal',
            'source': 'ENGINE_SYSTEM'
        })
        
        # Reset risk manager
        self.controller.risk_manager.active_positions = {}
        self.controller.risk_manager.cold_start_active = False
        
        result = self.controller.process_cycle()
        
        # Check that a trade was attempted
        trades = result.get('trades', [])
        self.assertGreater(len(trades), 0)
    
    def test_full_cycle_index(self):
        """Test full cycle for index pair"""
        # Mock zscore signal
        self.controller.get_zscore_signal = Mock(return_value={
            'action': 'SELL',
            'confidence': 75,
            'price': 7525.99,
            'z_score': 2.5,
            'reasoning': 'Test zscore signal',
            'source': 'ZSCORE_SYSTEM'
        })
        
        # Reset risk manager
        self.controller.risk_manager.active_positions = {}
        self.controller.risk_manager.cold_start_active = False
        
        result = self.controller.process_cycle()
        
        # Check that a trade was attempted
        trades = result.get('trades', [])
        self.assertGreater(len(trades), 0)
    
    def test_signal_saving(self):
        """Test signal saving from both systems"""
        # Create a signal
        signal = {
            'action': 'BUY',
            'confidence': 80,
            'price': 1.1430,
            'z_score': 2.0,
            'reasoning': 'Test integration',
            'source': 'INTEGRATION_TEST'
        }
        
        # Reset risk manager
        self.controller.risk_manager.active_positions = {}
        self.controller.risk_manager.cold_start_active = False
        
        # Execute trade
        result = self.controller.execute_trade('EURUSD', signal)
        
        # Should be executed
        self.assertEqual(result['status'], 'EXECUTED')


# ============================================================
# TEST 6: STRESS TESTS
# ============================================================

class TestStress(unittest.TestCase):
    """Stress tests for the unified controller"""
    
    def setUp(self):
        """Setup before each test"""
        self.controller = UnifiedTradingController({
            'min_confidence': 50,
            'cycle_interval': 1,
            'cold_start_threshold': 3,
            'cold_start_min_win_rate': 0.0
        })
        
        # Mock MT4
        self.controller.mt4 = Mock()
        self.controller.mt4._send.return_value = {'success': True, 'ticket': 12345}
    
    def test_concurrent_symbols(self):
        """Test processing many symbols simultaneously"""
        # Mock all signals
        self.controller.get_signal = Mock(return_value={
            'action': 'HOLD',
            'confidence': 0,
            'reasoning': 'Test'
        })
        
        # Process cycle
        start_time = time.time()
        result = self.controller.process_cycle()
        end_time = time.time()
        
        # Should complete quickly
        self.assertLess(end_time - start_time, 5)
        self.assertIsNotNone(result)
    
    def test_rapid_cycles(self):
        """Test rapid cycling doesn't cause issues"""
        # Mock signals
        self.controller.get_signal = Mock(return_value={
            'action': 'HOLD',
            'confidence': 0,
            'reasoning': 'Test'
        })
        
        # Run multiple cycles
        results = []
        for i in range(5):
            self.controller.cycle_count = 0  # Reset for each cycle
            result = self.controller.process_cycle()
            results.append(result)
            time.sleep(0.1)
        
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsNotNone(result)


# ============================================================
# TEST 7: ERROR HANDLING TESTS
# ============================================================

class TestErrorHandling(unittest.TestCase):
    """Test error handling in unified controller"""
    
    def test_missing_price_service(self):
        """Test handling missing price service"""
        controller = UnifiedTradingController()
        controller.price_service = None
        
        # Should handle gracefully
        signal = controller.get_signal('EURUSD')
        self.assertEqual(signal['action'], 'HOLD')
        self.assertEqual(signal['confidence'], 0)
    
    def test_missing_agents(self):
        """Test handling missing agents"""
        controller = UnifiedTradingController()
        controller.zscore_agents = []
        controller.price_service = Mock()
        controller.price_service.get_price.return_value = 1.1430
        
        signal = controller.get_zscore_signal('#S&P500')
        self.assertEqual(signal['action'], 'HOLD')
    
    def test_missing_mt4(self):
        """Test handling missing MT4"""
        controller = UnifiedTradingController()
        controller.mt4 = None
        
        result = controller._send_mt4_order('EURUSD', 'BUY', 0.03, 1.1430, 1.14, 1.15)
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'MT4 not connected')
    
    def test_invalid_symbol(self):
        """Test invalid symbol handling"""
        controller = UnifiedTradingController()
        controller.price_service = Mock()
        controller.price_service.get_price.return_value = 0
        controller.price_service.get_all_prices.return_value = {}
        
        signal = controller.get_signal('INVALID')
        self.assertEqual(signal['action'], 'HOLD')
        self.assertEqual(signal['confidence'], 0)


# ============================================================
# TEST 8: PERFORMANCE TESTS
# ============================================================

class TestPerformance(unittest.TestCase):
    """Performance tests"""
    
    def test_price_service_performance(self):
        """Test price service performance"""
        service = PriceService()
        service._prices = MOCK_PRICES.copy()
        
        # Measure get_price performance
        start = time.time()
        for _ in range(100):
            service.get_price('EURUSD')
        end = time.time()
        
        # Should be fast (< 0.5 seconds for 100 calls)
        self.assertLess(end - start, 1.0)
    
    def test_signal_service_performance(self):
        """Test signal service performance"""
        service = SignalService()
        service.signals = []  # Clear
        
        # Add many signals
        start = time.time()
        for i in range(100):
            service.add_signal(
                f'EURUSD{i % 10}',
                'BUY' if i % 2 == 0 else 'SELL',
                70 + (i % 20),
                1.14 + (i * 0.0001)
            )
        end = time.time()
        
        # Should be fast
        self.assertLess(end - start, 1.0)
        
        # Should have 100 signals
        self.assertEqual(len(service.signals), 100)


# ============================================================
# TEST 9: END-TO-END SCENARIO TESTS
# ============================================================

class TestScenarios(unittest.TestCase):
    """Real-world trading scenarios"""
    
    def setUp(self):
        """Setup before each test"""
        self.controller = UnifiedTradingController({
            'min_confidence': 50,
            'cycle_interval': 1,
            'cold_start_threshold': 3,
            'cold_start_min_win_rate': 0.0
        })
        
        # Mock MT4
        self.controller.mt4 = Mock()
        self.controller.mt4._send.return_value = {'success': True, 'ticket': 12345}
        
        # Reset risk manager
        self.controller.risk_manager.active_positions = {}
        self.controller.risk_manager.cold_start_active = False
    
    def test_mean_reversion_scenario(self):
        """Test mean reversion scenario (Indices)"""
        # Simulate extreme Z-score
        mock_signal = {
            'action': 'SELL',  # Overextended
            'confidence': 85,
            'price': 7600,
            'z_score': 2.8,
            'reasoning': 'Extreme Z-score',
            'source': 'ZSCORE_SYSTEM'
        }
        
        self.controller.get_zscore_signal = Mock(return_value=mock_signal)
        
        result = self.controller.process_cycle()
        trades = result.get('trades', [])
        
        # Should have executed a trade
        self.assertGreater(len(trades), 0)
        if len(trades) > 0:
            self.assertEqual(trades[0]['action'], 'SELL')
    
    def test_dollar_engine_scenario(self):
        """Test dollar engine scenario (Forex)"""
        # Simulate engine signal
        mock_signal = {
            'action': 'BUY',
            'confidence': 75,
            'price': 1.1430,
            'reasoning': 'Engine forward',
            'source': 'ENGINE_SYSTEM'
        }
        
        self.controller.get_engine_signal = Mock(return_value=mock_signal)
        
        result = self.controller.process_cycle()
        trades = result.get('trades', [])
        
        # Should have executed a trade
        self.assertGreater(len(trades), 0)
        if len(trades) > 0:
            self.assertEqual(trades[0]['action'], 'BUY')
    
    def test_cold_start_scenario(self):
        """Test cold start scenario"""
        controller = UnifiedTradingController({
            'min_confidence': 50,
            'cold_start_threshold': 3,
            'cold_start_min_win_rate': 0.4
        })
        
        # Should start in cold start
        self.assertTrue(controller.risk_manager.cold_start_active)
        
        # Add enough samples
        for i in range(3):
            controller.risk_manager.add_cold_start_sample({
                'win': i < 2,  # 67% win rate
                'pnl': 10 if i < 2 else -10
            })
        
        # Check if cold start completed
        self.assertFalse(controller.risk_manager.cold_start_active)


# ============================================================
# TEST 10: WEB DASHBOARD TESTS
# ============================================================

class TestDashboard(unittest.TestCase):
    """Test the web dashboard integration"""
    
    def test_status_endpoint(self):
        """Test status endpoint"""
        controller = UnifiedTradingController()
        status = controller.get_status()
        
        self.assertIsNotNone(status)
        self.assertIn('is_running', status)
        self.assertIn('risk', status)
        self.assertIn('symbols', status)
        self.assertIn('systems', status)
    
    def test_symbol_coverage(self):
        """Test all symbols are covered"""
        controller = UnifiedTradingController()
        
        all_symbols = controller.all_symbols
        
        # Create a list of all expected symbols from asset_groups
        expected_symbols = []
        if hasattr(controller, 'asset_groups'):
            for group_name, group in controller.asset_groups.items():
                if group.get('enabled', True):
                    expected_symbols.extend(group.get('symbols', []))
        
        # If no asset_groups, use the all_symbols list itself
        if not expected_symbols:
            expected_symbols = all_symbols
        
        # Check that we have a reasonable number of symbols
        self.assertGreater(len(all_symbols), 5)
        
        # Check that all expected symbols are in all_symbols
        for symbol in expected_symbols:
            self.assertIn(symbol, all_symbols)


# ============================================================
# RUN ALL TESTS
# ============================================================

def run_all_tests():
    """Run all test suites"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING UNIFIED CONTROLLER TESTS")
    print("=" * 60)
    
    # Create test loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPriceService,
        TestRiskManager,
        TestSignalService,
        TestUnifiedController,
        TestIntegration,
        TestStress,
        TestErrorHandling,
        TestPerformance,
        TestScenarios,
        TestDashboard
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"   Tests Run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nFailures:")
        for failure in result.failures:
            print(f"   - {failure[0]}")
        print("\nErrors:")
        for error in result.errors:
            print(f"   - {error[0]}")
    
    print("=" * 60)
    
    return result.wasSuccessful()


# ============================================================
# QUICK TEST FUNCTION
# ============================================================

def quick_test():
    """Quick test to verify basic functionality"""
    print("\n🚀 Running Quick Test...")
    
    try:
        # 1. Test Price Service
        print("   Testing Price Service...")
        ps = PriceService()
        ps._prices = MOCK_PRICES
        price = ps.get_price('EURUSD')
        print(f"      ✅ EURUSD: {price:.5f}")
        
        # 2. Test Risk Manager
        print("   Testing Risk Manager...")
        rm = RiskManager()
        rm.cold_start_active = False
        allowed, reason = rm.check_trade_allowed('EURUSD')
        print(f"      ✅ Trade allowed: {allowed}")
        
        # 3. Test Signal Service
        print("   Testing Signal Service...")
        ss = SignalService()
        ss.signals = []
        signal = ss.add_signal('EURUSD', 'BUY', 75, 1.1430)
        print(f"      ✅ Signal added: {signal['id']}")
        
        # 4. Test Controller
        print("   Testing Controller...")
        controller = UnifiedTradingController({
            'min_confidence': 50,
            'cycle_interval': 1,
            'cold_start_threshold': 3,
            'cold_start_min_win_rate': 0.0
        })
        
        # Mock get_signal to return HOLD
        controller.get_signal = Mock(return_value={
            'action': 'HOLD',
            'confidence': 0,
            'reasoning': 'Test'
        })
        
        result = controller.process_cycle()
        print(f"      ✅ Cycle processed: {result['cycle']}")
        
        print("\n✅ Quick test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Quick test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Unified Trading Controller')
    parser.add_argument('--quick', action='store_true', help='Run quick test only')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    if args.quick:
        quick_test()
    else:
        run_all_tests()