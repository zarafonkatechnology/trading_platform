# agents/forex_agent_u_enhanced.py - Enhanced with Better Detection

"""
Agent_U Enhanced - More Realistic Liquidity Detection
Now with improved cluster detection and better Monte Carlo
"""

import math
import random
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple, Any

# Try imports with fallbacks
try:
    from .base_agent import BaseAgent
except ImportError:
    class BaseAgent:
        def __init__(self, name: str, agent_type: str, specialization: str):
            self.name = name
            self.agent_type = agent_type
            self.specialization = specialization

try:
    from price_cache_manager import get_price_for_agent, get_any_price
    from price_helper import get_price_with_fallback, get_price_with_details
except ImportError:
    def get_price_with_fallback(symbol, agent_name):
        return 1.1000
    def get_price_with_details(symbol):
        return {'success': True, 'mid': 1.1000, 'bid': 1.0999, 'ask': 1.1001}
    def get_any_price():
        return 1.1000
    def get_price_for_agent(symbol, agent_name):
        return {'success': True, 'mid': 1.1000}


class ForexLiquidityAgentEnhanced(BaseAgent):
    """
    Enhanced Agent U - More realistic liquidity detection
    """
    
    def __init__(self, name: str = "Forex_Agent_U_Enhanced"):
        super().__init__(
            name=name,
            agent_type="Forex Liquidity & Stop Hunting Specialist",
            specialization="Detects institutional order flow, liquidity clusters, and stop runs"
        ) 
        self.name = name
        self.agent_type = "Forex Liquidity & Stop Hunting Specialist"
        # === FOREX PAIRS CONFIGURATION ===
        self.forex_pairs = {
            'EURUSD': {'type': 'INVERSE', 'gear_ratio': 1.2, 'pip_value': 0.0001, 'decimals': 5},
            'GBPUSD': {'type': 'INVERSE', 'gear_ratio': 1.1, 'pip_value': 0.0001, 'decimals': 5},
            'USDJPY': {'type': 'DIRECT', 'gear_ratio': 0.8, 'pip_value': 0.01, 'decimals': 3},
            'AUDUSD': {'type': 'INVERSE', 'gear_ratio': 0.9, 'pip_value': 0.0001, 'decimals': 5},
            'USDCAD': {'type': 'DIRECT', 'gear_ratio': 0.7, 'pip_value': 0.0001, 'decimals': 5},
            'EURGBP': {'type': 'CROSS', 'gear_ratio': 0.5, 'pip_value': 0.0001, 'decimals': 5},
            'EURJPY': {'type': 'CROSS', 'gear_ratio': 0.6, 'pip_value': 0.01, 'decimals': 3},
        }
        
        # === LIQUIDITY TRACKING ===
        self.liquidity_history = deque(maxlen=200)
        self.price_history = defaultdict(lambda: deque(maxlen=100))
        self.stop_clusters = defaultdict(list)
        
        # === KEY LEVELS ===
        self.key_levels = defaultdict(set)
        self._generate_key_levels()
        
        # === ENGINE STATE ===
        self.engine_speed = 0.0
        self.engine_direction = 'NEUTRAL'
        self.engine_health = 100.0
        
        # === STATISTICS ===
        self.stats = {
            'liquidity_grabs': 0,
            'stop_runs_detected': 0,
            'successful_trades': 0,
            'avg_reward': 0
        }
        
        print(f"   ✅ {self.name} initialized")
        print(f"      📊 Tracking: {len(self.forex_pairs)} pairs")
        print(f"      🎯 Key levels generated: {sum(len(v) for v in self.key_levels.values())}")
    
    def _generate_key_levels(self):
        """Generate key psychological levels for each pair"""
        for pair, config in self.forex_pairs.items():
            levels = set()
            
            # Get base price for this pair
            base_price = self._get_base_price(pair)
            pip_value = config['pip_value']
            
            # Generate levels around current price
            for i in range(-20, 21):
                level = base_price + (i * 100 * pip_value)
                levels.add(round(level, config['decimals']))
            
            # Add round numbers (every 50 pips)
            for i in range(-40, 41):
                level = base_price + (i * 50 * pip_value)
                levels.add(round(level, config['decimals']))
            
            # Add major levels (every 1000 pips)
            for i in range(-5, 6):
                level = base_price + (i * 1000 * pip_value)
                levels.add(round(level, config['decimals']))
            
            self.key_levels[pair] = levels
    
    
    def _get_base_price(self, pair: str) -> float:
        """Get base price for a pair"""
        base_prices = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.3000,
            'USDJPY': 150.00,
            'AUDUSD': 0.6500,
            'USDCAD': 1.3500,
            'EURGBP': 0.8500,
            'EURJPY': 165.00,
        }
        return base_prices.get(pair, 1.0000)
    
    def analyze(self, signal_data: Dict) -> Dict:
        """Main analysis method with enhanced detection"""
        symbol = signal_data.get('symbol', 'EURUSD')
        current_price = signal_data.get('price', 0.0)
        
        # Get price with fallback
        if current_price <= 0:
            current_price = self._get_base_price(symbol)
        
        # Get pair config
        pair_config = self.forex_pairs.get(symbol, self.forex_pairs['EURUSD'])
        
        # Update price history
        self.price_history[symbol].append(current_price)
        
        # Update engine state
        if 'engine_state' in signal_data:
            engine = signal_data['engine_state']
            self.engine_speed = engine.get('engine_speed', 0.0)
            self.engine_direction = engine.get('engine_direction', 'NEUTRAL')
            self.engine_health = engine.get('engine_health', 100.0)
        
        # === 1. FIND NEAREST KEY LEVELS ===
        nearest_levels = self._find_nearest_levels(current_price, symbol, pair_config)
        
        # === 2. DETECT LIQUIDITY CLUSTERS ===
        clusters = self._detect_liquidity_clusters(current_price, symbol, pair_config, nearest_levels)
        
        # === 3. DETECT STOP RUN ===
        stop_run = self._detect_stop_run(current_price, symbol, pair_config, clusters)
        
        # === 4. DETECT INSTITUTIONAL FLOW ===
        flow = self._detect_institutional_flow(current_price, symbol, pair_config)
        
        # === 5. GENERATE SIGNAL ===
        signal = self._generate_signal(current_price, clusters, stop_run, flow, symbol, pair_config)
        
        # === 6. MONTE CARLO ===
        monte_carlo = self.monte_carlo_forecast(
            current_price,
            volatility=0.005,
            n_sims=1000,
            horizon=20
        )
        
        return {
            'agent': self.name,
            'symbol': symbol,
            'vote': signal['vote'],
            'confidence': signal['confidence'],
            'reasoning': signal['reasoning'],
            'entry_price': signal.get('entry_price', current_price),
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('take_profit'),
            'position_size': signal.get('position_size', 0.01),
            
            # Detailed info
            'nearest_levels': nearest_levels,
            'liquidity_clusters': clusters,
            'stop_run': stop_run,
            'institutional_flow': flow,
            'engine_alignment': signal.get('engine_aligned', False),
            'engine_direction': self.engine_direction,
            
            'monte_carlo': monte_carlo,
            'gear_type': pair_config['type'],
            
            'timestamp': datetime.now().isoformat()
        }
    
    def _find_nearest_levels(self, price: float, symbol: str, config: Dict) -> Dict:
        """Find nearest key levels above and below current price"""
        pip_value = config['pip_value']
        levels = self.key_levels.get(symbol, set())
        
        if not levels:
            return {'above': None, 'below': None, 'nearest': None}
        
        # Sort levels
        sorted_levels = sorted(levels)
        
        # Find levels above and below
        above = None
        below = None
        
        for level in sorted_levels:
            if level > price:
                above = level
                break
            elif level < price:
                below = level
        
        # Calculate distances in pips
        result = {
            'above': above,
            'below': below,
            'nearest': None,
            'distances': {}
        }
        
        if above:
            distance_pips = (above - price) / pip_value
            result['distances']['above'] = round(distance_pips, 1)
        
        if below:
            distance_pips = (price - below) / pip_value
            result['distances']['below'] = round(distance_pips, 1)
        
        # Find nearest
        if above and below:
            if (above - price) < (price - below):
                result['nearest'] = {'level': above, 'direction': 'above', 'distance': result['distances']['above']}
            else:
                result['nearest'] = {'level': below, 'direction': 'below', 'distance': result['distances']['below']}
        elif above:
            result['nearest'] = {'level': above, 'direction': 'above', 'distance': result['distances']['above']}
        elif below:
            result['nearest'] = {'level': below, 'direction': 'below', 'distance': result['distances']['below']}
        
        return result
    
    def _detect_liquidity_clusters(self, price: float, symbol: str, config: Dict, levels: Dict) -> Dict:
        """Detect liquidity clusters around key levels"""
        pip_value = config['pip_value']
        clusters = []
        
        # Check if price is near a key level (within 20 pips)
        if levels['nearest']:
            distance = levels['nearest']['distance']
            level = levels['nearest']['level']
            
            if distance < 20:
                # This is a liquidity cluster
                cluster_size = self._estimate_cluster_size(distance, config)
                clusters.append({
                    'level': level,
                    'distance_pips': distance,
                    'size_millions': cluster_size,
                    'type': 'KEY_LEVEL',
                    'direction': levels['nearest']['direction']
                })
        
        # Check for previous day's high/low (simulated)
        if len(self.price_history[symbol]) > 20:
            prices = list(self.price_history[symbol])
            day_high = max(prices[-20:])
            day_low = min(prices[-20:])
            
            # Check if price is near day's high/low
            for level, name in [(day_high, 'DAY_HIGH'), (day_low, 'DAY_LOW')]:
                distance = abs(price - level) / pip_value
                if distance < 30:
                    cluster_size = self._estimate_cluster_size(distance, config) * 0.7
                    clusters.append({
                        'level': level,
                        'distance_pips': distance,
                        'size_millions': cluster_size,
                        'type': name,
                        'direction': 'above' if level > price else 'below'
                    })
        
        # Determine if there's a significant cluster
        if clusters:
            # Find nearest cluster
            nearest = min(clusters, key=lambda x: x['distance_pips'])
            
            return {
                'detected': True,
                'clusters': clusters,
                'nearest': nearest,
                'is_stop_hunt_target': nearest['distance_pips'] < 15,
                'total_size': sum(c['size_millions'] for c in clusters)
            }
        
        return {'detected': False, 'clusters': [], 'nearest': None, 'is_stop_hunt_target': False}
    
    def _detect_stop_run(self, price: float, symbol: str, config: Dict, clusters: Dict) -> Dict:
        """Detect if a stop run is in progress"""
        # Check engine reversal probability
        engine_reversing = self.engine_speed < 0 and self.engine_health < 60
        
        # Check if price has broken through a key level
        if clusters['detected'] and clusters['is_stop_hunt_target']:
            nearest = clusters['nearest']
            
            # Determine direction of stop run
            if nearest['direction'] == 'above':
                # Price moving above key level = buy stop run
                direction = 'BUY'
                reason = f"Price breaking above key level {nearest['level']:.5f} ({nearest['distance_pips']} pips)"
            else:
                # Price moving below key level = sell stop run
                direction = 'SELL'
                reason = f"Price breaking below key level {nearest['level']:.5f} ({nearest['distance_pips']} pips)"
            
            # Check engine alignment
            engine_aligned = self._check_engine_alignment(direction, config['type'])
            
            if engine_aligned:
                return {
                    'in_progress': True,
                    'direction': direction,
                    'reason': reason,
                    'confidence': 85,
                    'level': nearest['level'],
                    'engine_aligned': True
                }
            else:
                return {
                    'in_progress': True,
                    'direction': 'HOLD',
                    'reason': f"Stop run detected but engine {self.engine_direction} - waiting",
                    'confidence': 60,
                    'level': nearest['level'],
                    'engine_aligned': False
                }
        
        # Check for general stop run conditions
        if engine_reversing and clusters['detected']:
            return {
                'in_progress': True,
                'direction': 'BUY' if self.engine_speed < 0 else 'SELL',
                'reason': f"Engine reversal detected near liquidity cluster",
                'confidence': 70,
                'level': clusters['nearest']['level'],
                'engine_aligned': True
            }
        
        return {
            'in_progress': False,
            'direction': 'HOLD',
            'reason': '',
            'confidence': 0,
            'engine_aligned': False
        }
    
    def _detect_institutional_flow(self, price: float, symbol: str, config: Dict) -> Dict:
        """Detect institutional flow patterns"""
        # Check for signs of institutional activity
        signals = []
        
        # 1. Check price action patterns
        if len(self.price_history[symbol]) > 20:
            prices = list(self.price_history[symbol])
            recent = prices[-10:]
            
            # Check for accumulation pattern (higher lows)
            lower_lows = sum(1 for i in range(1, len(recent)) if recent[i] < recent[i-1])
            if lower_lows < 3:  # Few lower lows = possible accumulation
                signals.append({'type': 'ACCUMULATION', 'strength': 0.6})
            
            # Check for distribution pattern (lower highs)
            higher_highs = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
            if higher_highs < 3:  # Few higher highs = possible distribution
                signals.append({'type': 'DISTRIBUTION', 'strength': 0.6})
        
        # 2. Check key level breaks with volume (simulated)
        if len(signals) >= 2:
            return {
                'detected': True,
                'direction': 'BUY' if 'ACCUMULATION' in str(signals) else 'SELL',
                'strength': 0.7,
                'signals': signals,
                'reason': f"Institutional flow detected: {signals[0]['type']}"
            }
        
        return {
            'detected': False,
            'direction': 'NEUTRAL',
            'strength': 0,
            'signals': [],
            'reason': 'No institutional flow detected'
        }
    
    def _generate_signal(self, price: float, clusters: Dict, stop_run: Dict, 
                        flow: Dict, symbol: str, config: Dict) -> Dict:
        """Generate final trading signal"""
        # Priority 1: Stop run in progress
        if stop_run['in_progress'] and stop_run['confidence'] > 70:
            if stop_run['engine_aligned']:
                pip_value = config['pip_value']
                entry_price = stop_run['level']
                
                if stop_run['direction'] == 'BUY':
                    stop_loss = entry_price - (pip_value * 20)
                    take_profit = entry_price + (pip_value * 40)
                    position_size = 0.02
                else:
                    stop_loss = entry_price + (pip_value * 20)
                    take_profit = entry_price - (pip_value * 40)
                    position_size = 0.02
                
                return {
                    'vote': stop_run['direction'],
                    'confidence': stop_run['confidence'],
                    'reasoning': f"⚡ STOP RUN: {stop_run['reason']} | Entry at {entry_price:.5f}",
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'engine_aligned': True
                }
        
        # Priority 2: Liquidity cluster watch
        elif clusters['detected'] and clusters['is_stop_hunt_target']:
            nearest = clusters['nearest']
            return {
                'vote': 'WATCH',
                'confidence': 75,
                'reasoning': f"📊 LIQUIDITY CLUSTER: {nearest['size_millions']:.1f}M at {nearest['level']:.5f} ({nearest['distance_pips']} pips)",
                'entry_price': price,
                'stop_loss': None,
                'take_profit': None,
                'position_size': 0.01,
                'engine_aligned': self._check_engine_alignment('BUY', config['type'])
            }
        
        # Priority 3: Engine direction
        elif abs(self.engine_speed) > 0.3:
            if self.engine_direction == 'FORWARD':
                if config['type'] == 'INVERSE':
                    vote = 'SELL'
                else:
                    vote = 'BUY'
            else:
                if config['type'] == 'INVERSE':
                    vote = 'BUY'
                else:
                    vote = 'SELL'
            
            return {
                'vote': vote,
                'confidence': 60,
                'reasoning': f"Engine {self.engine_direction} ({self.engine_speed:.2f}) - {config['type']} gear",
                'entry_price': price,
                'stop_loss': None,
                'take_profit': None,
                'position_size': 0.01,
                'engine_aligned': True
            }
        
        # Priority 4: Hold
        return {
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': "No clear signals - waiting for setup",
            'entry_price': price,
            'stop_loss': None,
            'take_profit': None,
            'position_size': 0,
            'engine_aligned': False
        }
    
    def _check_engine_alignment(self, signal_direction: str, gear_type: str) -> bool:
        """Check if signal direction aligns with engine"""
        if self.engine_speed == 0:
            self.engine_direction = 'NEUTRAL'
        
        if gear_type == 'INVERSE':
            if signal_direction == 'BUY' and self.engine_direction == 'BACKWARD':
                return True
            if signal_direction == 'SELL' and self.engine_direction == 'FORWARD':
                return True
        elif gear_type == 'DIRECT':
            if signal_direction == 'BUY' and self.engine_direction == 'FORWARD':
                return True
            if signal_direction == 'SELL' and self.engine_direction == 'BACKWARD':
                return True
        
        return False
    
    def _estimate_cluster_size(self, distance_pips: float, config: Dict) -> float:
        if distance_pips < 5:
               return random.uniform(30, 60)  # ← This is actually correct syntax
        elif distance_pips < 15:
               return random.uniform(15, 35)
        elif distance_pips < 30:
               return random.uniform(8, 20)
        else:
               return random.uniform(3, 10)
    
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005,
                           n_sims: int = 1000, horizon: int = 20) -> Dict:
        """Monte Carlo simulation with improved accuracy"""
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
        final_prices = []
        
        for _ in range(n_sims):
            price = current_price
            for _ in range(horizon):
                # Random walk with realistic drift
                drift = random.gauss(0.0001, 0.00005)
                shock = random.gauss(0, volatility)
                price *= (1 + drift + shock)
            
            final_prices.append(price)
            
            # Cloud levels
            cloud_top = current_price * (1 + volatility * 1.5)
            cloud_bottom = current_price * (1 - volatility * 1.5)
            
            if price > cloud_top:
                outcomes['above_cloud'] += 1
            elif price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
        
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
        
        # Calculate stats
        mean_price = sum(final_prices) / n_sims
        std_price = (sum((p - mean_price) ** 2 for p in final_prices) / n_sims) ** 0.5
        
        # Determine signal
        if probs['above_cloud'] > 55:
            vote = 'BUY'
            confidence = probs['above_cloud']
        elif probs['below_cloud'] > 55:
            vote = 'SELL'
            confidence = probs['below_cloud']
        else:
            vote = 'HOLD'
            confidence = probs['inside_cloud'] + 20
        
        return {
            'vote': vote,
            'confidence': min(95, confidence),
            'probabilities': probs,
            'mean_price': round(mean_price, 5),
            'std_dev': round(std_price, 5),
            'expected_range': {
                'low': round(mean_price - 2 * std_price, 5),
                'high': round(mean_price + 2 * std_price, 5)
            }
        }


# Test
def main():
    print("=" * 60)
    print("Testing Enhanced Forex Liquidity Agent")
    print("=" * 60)
    
    agent = ForexLiquidityAgentEnhanced()
    
    # Test with different scenarios
    test_cases = [
        {'symbol': 'EURUSD', 'price': 1.1000, 'engine_state': {'engine_speed': 0.5, 'engine_direction': 'FORWARD', 'engine_health': 90}},
        {'symbol': 'GBPUSD', 'price': 1.3000, 'engine_state': {'engine_speed': -0.4, 'engine_direction': 'BACKWARD', 'engine_health': 85}},
        {'symbol': 'USDJPY', 'price': 150.00, 'engine_state': {'engine_speed': 0.6, 'engine_direction': 'FORWARD', 'engine_health': 95}},
    ]
    
    for i, data in enumerate(test_cases, 1):
        print(f"\n📊 Test Case {i}: {data['symbol']} at {data['price']}")
        print("-" * 40)
        
        result = agent.analyze(data)
        
        print(f"   Vote: {result['vote']}")
        print(f"   Confidence: {result['confidence']}%")
        print(f"   Reasoning: {result['reasoning']}")
        
        if result['liquidity_clusters']['detected']:
            print(f"   🎯 Liquidity: {result['liquidity_clusters']['nearest']['distance_pips']} pips away")
        
        if result['stop_run']['in_progress']:
            print(f"   ⚡ Stop Run: {result['stop_run']['direction']}")
        
        print(f"   📈 Monte Carlo: {result['monte_carlo']['vote']} ({result['monte_carlo']['confidence']}%)")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete")

if __name__ == "__main__":
    main()