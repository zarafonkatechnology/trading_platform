"""
Momentum Burst Strategy with Agent Consultation
- Consults Dark Pool agents (P, Q, G) before trading
- Runs Monte Carlo simulations for probability
- Only executes if multiple agents agree
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class AgentConsultationResult:
    """Result from consulting an agent"""
    agent_name: str
    vote: str  # BUY, SELL, HOLD
    confidence: float
    reasoning: str
    weight: float = 1.0


class MomentumWithAgentConsultation:
    """
    Momentum burst strategy that consults:
    1. Dark Pool Agents (P, Q, G) - whale activity
    2. Monte Carlo simulation - probability analysis
    3. Volume Master (Agent_J) - volume confirmation
    4. Volatility Agent (Agent_D) - risk assessment
    """
    
    def __init__(self):
        # Agent weights for momentum trading
        self.agent_weights = {
            'Agent_P': 1.2,   # Whisper - dark pool leaks
            'Agent_Q': 1.3,   # Dark Pool Whale - FINRA data
            'Agent_G': 1.1,   # Whale Tracker - COT data
            'Agent_J': 1.0,   # Volume Master
            'Agent_D': 0.8,   # Volatility (lower weight)
            'Agent_C': 1.0    # Momentum
        }
        
        # Minimum votes needed to trade
        self.min_votes_required = 3
        self.min_avg_confidence = 65
        self.consultation_history = []


def get_asset_parameters(asset: str) -> Dict:
    """
    Return asset-specific parameters for price calculations.
    """
    params = {
        # Forex majors
        'EURUSD': {'pip_size': 0.0001, 'normal_range_pips': 80, 'volatility_factor': 1.0, 'decimals': 4},
        'GBPUSD': {'pip_size': 0.0001, 'normal_range_pips': 80, 'volatility_factor': 1.0, 'decimals': 4},
        'USDJPY': {'pip_size': 0.01, 'normal_range_pips': 80, 'volatility_factor': 0.8, 'decimals': 2},
        'USDCHF': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
        'AUDUSD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
        'USDCAD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
        'NZDUSD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
        
        # Metals
        'XAU/USD': {'pip_size': 0.01, 'normal_range_pips': 2000, 'volatility_factor': 1.2, 'decimals': 2},
        'XAG/USD': {'pip_size': 0.001, 'normal_range_pips': 50, 'volatility_factor': 1.1, 'decimals': 3},
        
        # Indices
        'NAS100/USD': {'pip_size': 0.1, 'normal_range_pips': 200, 'volatility_factor': 1.3, 'decimals': 1},
        'S&P500/USD': {'pip_size': 0.1, 'normal_range_pips': 50, 'volatility_factor': 1.0, 'decimals': 1},
        'DJ30/USD': {'pip_size': 0.1, 'normal_range_pips': 150, 'volatility_factor': 1.1, 'decimals': 1},
        
        # Commodities
        'BCO/USD': {'pip_size': 0.01, 'normal_range_pips': 200, 'volatility_factor': 1.2, 'decimals': 2},
        'WTICO/USD': {'pip_size': 0.01, 'normal_range_pips': 200, 'volatility_factor': 1.2, 'decimals': 2},
    }
    
    # Also handle alternative naming conventions
    asset_aliases = {
        'GOLD': 'XAU/USD',
        'GOLD': 'XAU/USD',
        'NAS100': 'NAS100/USD',
        'S&P500': 'S&P500/USD',
        'DJ30': 'DJ30/USD',
        'UK100': 'UK100/GBP',
    }
    
    if asset in asset_aliases:
        asset = asset_aliases[asset]
    
    return params.get(asset, {'pip_size': 0.0001, 'normal_range_pips': 80, 'volatility_factor': 1.0, 'decimals': 4})


def calculate_realistic_range(asset: str, current_price: float, volume_ratio: float) -> Dict:
    """
    Calculate realistic price range based on asset type.
    """
    params = get_asset_parameters(asset)
    pip_size = params['pip_size']
    normal_range_pips = params['normal_range_pips']
    decimals = params['decimals']
    
    # Calculate expected move in pips based on volume spike
    if volume_ratio > 2.5:
        expected_pips = normal_range_pips * 0.6
        confidence = 85
    elif volume_ratio > 2.0:
        expected_pips = normal_range_pips * 0.5
        confidence = 75
    elif volume_ratio > 1.5:
        expected_pips = normal_range_pips * 0.35
        confidence = 65
    elif volume_ratio > 1.2:
        expected_pips = normal_range_pips * 0.2
        confidence = 55
    else:
        expected_pips = normal_range_pips * 0.1
        confidence = 45
    
    # Convert pips to price
    expected_move_price = expected_pips * pip_size
    
    # Cap by normal daily range (never exceed)
    max_move_pips = normal_range_pips * 0.8
    max_move_price = max_move_pips * pip_size
    
    actual_move = min(expected_move_price, max_move_price)
    actual_pips = actual_move / pip_size
    
    return {
        'expected_low': round(current_price - actual_move, decimals),
        'expected_high': round(current_price + actual_move, decimals),
        'expected_pips': round(actual_pips, 1),
        'max_pips_possible': normal_range_pips,
        'is_realistic': actual_pips <= normal_range_pips,
        'confidence': confidence
    }
    def consult_dark_pool_agents(self, asset: str, current_price: float, 
                                  volume_ratio: float) -> List[AgentConsultationResult]:
        """
        Consult dark pool agents (P, Q, G) for whale activity.
        """
        results = []
        
        # Agent_P (Whisper) - Dark pool leaks
        dark_pool_ratio = self._estimate_dark_pool_ratio(asset, volume_ratio)
        
        if dark_pool_ratio > 40:
            vote = 'BUY' if volume_ratio > 1.5 else 'HOLD'
            confidence = min(95, 60 + dark_pool_ratio * 0.5)
            reasoning = f"High dark pool activity ({dark_pool_ratio:.0f}%) - whales accumulating"
        elif dark_pool_ratio > 25:
            vote = 'BUY'
            confidence = 65
            reasoning = f"Moderate dark pool activity ({dark_pool_ratio:.0f}%)"
        else:
            vote = 'HOLD'
            confidence = 40
            reasoning = f"Low dark pool activity ({dark_pool_ratio:.0f}%)"
        
        results.append(AgentConsultationResult(
            agent_name='Agent_P',
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.agent_weights['Agent_P']
        ))
        
        # Agent_Q (Dark Pool Whale) - FINRA TRF data
        whale_footprint = self._detect_whale_footprint(asset, volume_ratio)
        
        if whale_footprint['detected']:
            vote = whale_footprint['direction']
            confidence = whale_footprint['confidence']
            reasoning = f"Whale footprint detected: {whale_footprint['size_millions']:.1f}M at key level"
        else:
            vote = 'HOLD'
            confidence = 35
            reasoning = "No significant whale footprints"
        
        results.append(AgentConsultationResult(
            agent_name='Agent_Q',
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.agent_weights['Agent_Q']
        ))
        
        # Agent_G (Whale Tracker) - COT data
        cot_signal = self._analyze_cot_data(asset)
        
        if cot_signal['commercial_bias'] == 'bullish':
            vote = 'BUY'
            confidence = cot_signal['confidence']
            reasoning = f"Commercials net long ({cot_signal['net_percent']:.0f}% of open interest)"
        elif cot_signal['commercial_bias'] == 'bearish':
            vote = 'SELL'
            confidence = cot_signal['confidence']
            reasoning = f"Commercials net short ({cot_signal['net_percent']:.0f}% of open interest)"
        else:
            vote = 'HOLD'
            confidence = 45
            reasoning = "Commercials neutral"
        
        results.append(AgentConsultationResult(
            agent_name='Agent_G',
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.agent_weights['Agent_G']
        ))
        
        return results
    
    def consult_volume_agent(self, asset: str, volume_ratio: float, 
                              price_change_pct: float) -> AgentConsultationResult:
        """
        Consult Agent_J (Volume Master) for confirmation.
        """
        if volume_ratio > 2.0 and price_change_pct > 0:
            vote = 'BUY'
            confidence = min(90, 60 + volume_ratio * 10)
            reasoning = f"Volume surge ({volume_ratio:.1f}x) confirming upward move"
        elif volume_ratio > 1.5 and price_change_pct < 0:
            vote = 'SELL'
            confidence = min(90, 60 + volume_ratio * 10)
            reasoning = f"Volume surge ({volume_ratio:.1f}x) confirming downward move"
        elif volume_ratio > 1.2:
            vote = 'BUY' if price_change_pct > 0 else 'SELL'
            confidence = 60
            reasoning = f"Above-average volume ({volume_ratio:.1f}x)"
        else:
            vote = 'HOLD'
            confidence = 40
            reasoning = f"Normal volume ({volume_ratio:.1f}x), waiting for surge"
        
        return AgentConsultationResult(
            agent_name='Agent_J',
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            weight=self.agent_weights['Agent_J']
        )
    
    def run_monte_carlo_simulation(self, current_price: float, 
                                    volatility: float, 
                                    n_simulations: int = 1000,
                                    horizon_minutes: int = 8) -> Dict:
        """
        Run Monte Carlo simulation to predict price movement probability.
        
        Returns:
            Dictionary with win probability, expected return, confidence intervals
        """
        np.random.seed(42)
        
        # Simulate price paths
        dt = 1 / (60 / horizon_minutes)  # Time step
        returns = np.random.normal(0, volatility * np.sqrt(dt), 
                                   (n_simulations, horizon_minutes))
        cumulative_returns = np.exp(np.cumsum(returns, axis=1))
        final_prices = current_price * cumulative_returns[:, -1]
        
        # Calculate statistics
        mean_price = np.mean(final_prices)
        std_price = np.std(final_prices)
        
        # Win probability (price > entry)
        win_probability = np.sum(final_prices > current_price) / n_simulations * 100
        
        # Expected return
        expected_return_pct = (mean_price - current_price) / current_price * 100
        
        # Confidence intervals
        percentile_68 = (np.percentile(final_prices, 16), np.percentile(final_prices, 84))
        percentile_95 = (np.percentile(final_prices, 2.5), np.percentile(final_prices, 97.5))
        
        # Risk of large loss (>1%)
        large_loss_risk = np.sum(final_prices < current_price * 0.99) / n_simulations * 100
        
        return {
            'win_probability': round(win_probability, 1),
            'expected_return_pct': round(expected_return_pct, 2),
            'expected_price': round(mean_price, 2),
            'confidence_interval_68': (round(percentile_68[0], 2), round(percentile_68[1], 2)),
            'confidence_interval_95': (round(percentile_95[0], 2), round(percentile_95[1], 2)),
            'large_loss_risk': round(large_loss_risk, 1),
            'simulations': n_simulations
        }
    
    def _estimate_dark_pool_ratio(self, asset: str, volume_ratio: float) -> float:
        """Estimate dark pool volume percentage"""
        # Simplified estimation based on volume spike
        base_ratio = 20  # Normal dark pool ratio 20%
        if volume_ratio > 2.0:
            return min(65, base_ratio + (volume_ratio - 1) * 15)
        elif volume_ratio > 1.5:
            return min(50, base_ratio + (volume_ratio - 1) * 10)
        return base_ratio
    
    def _detect_whale_footprint(self, asset: str, volume_ratio: float) -> Dict:
        """Detect whale footprint from FINRA-like data"""
        if volume_ratio > 2.5:
            return {
                'detected': True,
                'direction': 'BUY',
                'confidence': 85,
                'size_millions': round(volume_ratio * 5, 1)
            }
        elif volume_ratio > 1.8:
            return {
                'detected': True,
                'direction': 'BUY',
                'confidence': 70,
                'size_millions': round(volume_ratio * 3, 1)
            }
        return {'detected': False, 'direction': 'NEUTRAL', 'confidence': 0, 'size_millions': 0}
    
    def _analyze_cot_data(self, asset: str) -> Dict:
        """Analyze COT data for commercial positioning"""
        # Simplified - in production, fetch from CFTC data
        return {
            'commercial_bias': 'bullish',
            'confidence': 65,
            'net_percent': 58
        }
    
    def _get_agent_consensus(self, consultation_results: List[AgentConsultationResult]) -> Dict:
        """Calculate weighted consensus from all consulted agents"""
        buy_weight = 0
        sell_weight = 0
        hold_weight = 0
        total_weight = 0
        
        for result in consultation_results:
            weight = result.weight * (result.confidence / 100)
            total_weight += weight
            
            if result.vote == 'BUY':
                buy_weight += weight
            elif result.vote == 'SELL':
                sell_weight += weight
            else:
                hold_weight += weight
        
        if total_weight == 0:
            return {'decision': 'HOLD', 'confidence': 0}
        
        buy_pct = (buy_weight / total_weight) * 100
        sell_pct = (sell_weight / total_weight) * 100
        hold_pct = (hold_weight / total_weight) * 100
        
        if buy_pct > sell_pct and buy_pct > hold_pct:
            decision = 'BUY'
            confidence = buy_pct
        elif sell_pct > buy_pct and sell_pct > hold_pct:
            decision = 'SELL'
            confidence = sell_pct
        else:
            decision = 'HOLD'
            confidence = hold_pct
        
        return {
            'decision': decision,
            'confidence': round(confidence, 1),
            'buy_percent': round(buy_pct, 1),
            'sell_percent': round(sell_pct, 1),
            'hold_percent': round(hold_pct, 1),
            'total_agents': len(consultation_results)
        }
    
    def should_trade(self, asset: str, current_price: float, 
                     volume_ratio: float, price_change_pct: float,
                     volatility: float) -> Tuple[bool, Dict]:
        """
        Main decision function - consults all agents and Monte Carlo.
        
        Returns:
            (should_trade, decision_details)
        """
        # Step 1: Consult all agents
        dark_pool_results = self.consult_dark_pool_agents(asset, current_price, volume_ratio)
        volume_result = self.consult_volume_agent(asset, volume_ratio, price_change_pct)
        
        all_results = dark_pool_results + [volume_result]
        
        # Step 2: Get agent consensus
        consensus = self._get_agent_consensus(all_results)
        
        # Step 3: Run Monte Carlo simulation
        monte_carlo = self.run_monte_carlo_simulation(current_price, volatility)
        
        # Step 4: Check dark pool alignment
        dark_pool_consensus = self._get_agent_consensus(dark_pool_results)
        
        # Step 5: Final decision logic
        should_trade = False
        decision_reasons = []
        
        # Condition 1: Agent consensus must be > 65% confidence
        if consensus['confidence'] >= 65:
            decision_reasons.append(f"Agent consensus: {consensus['decision']} ({consensus['confidence']:.0f}%)")
            
            # Condition 2: Dark pool agents must agree
            if dark_pool_consensus['decision'] == consensus['decision']:
                decision_reasons.append(f"Dark pool agents agree: {dark_pool_consensus['decision']}")
                
                # Condition 3: Monte Carlo must show win probability > 60%
                if monte_carlo['win_probability'] >= 60:
                    decision_reasons.append(f"Monte Carlo win prob: {monte_carlo['win_probability']:.0f}%")
                    
                    # Condition 4: Large loss risk must be < 20%
                    if monte_carlo['large_loss_risk'] < 20:
                        decision_reasons.append(f"Large loss risk: {monte_carlo['large_loss_risk']:.0f}%")
                        should_trade = True
                    else:
                        decision_reasons.append(f"❌ Large loss risk too high: {monte_carlo['large_loss_risk']:.0f}%")
                else:
                    decision_reasons.append(f"❌ Monte Carlo win prob too low: {monte_carlo['win_probability']:.0f}%")
            else:
                decision_reasons.append(f"❌ Dark pool agents disagree: {dark_pool_consensus['decision']} vs {consensus['decision']}")
        else:
            decision_reasons.append(f"❌ Agent consensus too low: {consensus['confidence']:.0f}%")
        
        # Special override: Dark pool whale footprint detected
        whale_footprint = self._detect_whale_footprint(asset, volume_ratio)
        if whale_footprint['detected'] and whale_footprint['confidence'] > 80:
            if monte_carlo['win_probability'] >= 55:
                should_trade = True
                decision_reasons.append(f"🐋 WHALE OVERRIDE: Large footprint detected ({whale_footprint['size_millions']:.1f}M)")
        
        result = {
            'should_trade': should_trade,
            'decision': consensus['decision'] if should_trade else 'HOLD',
            'confidence': consensus['confidence'],
            'agent_consensus': consensus,
            'dark_pool_consensus': dark_pool_consensus,
            'monte_carlo': monte_carlo,
            'agent_votes': [
                {
                    'agent': r.agent_name,
                    'vote': r.vote,
                    'confidence': r.confidence,
                    'reasoning': r.reasoning
                }
                for r in all_results
            ],
            'reasons': decision_reasons
        }
        
        # Store for history
        self.consultation_history.append({
            'timestamp': datetime.now().isoformat(),
            'asset': asset,
            'result': result
        })
        
        return should_trade, result
