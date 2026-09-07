# C:\trading_platform\forex_engine\brokers\broker_manager.py
"""
Broker Manager - Manages all pair brokers and coordinates decisions.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BrokerManager:
    """
    Manages all pair brokers with hierarchical decision flow.
    Flow: Pair Broker → Dollar Engine → Monte Carlo → Execution
    """
    
    def __init__(self, engine, monte_carlo, rl_agent=None):
        self.engine = engine
        self.monte_carlo = monte_carlo
        self.rl_agent = rl_agent
        
        self.brokers: Dict = {}
        self.decision_history = []
        
        logger.info("✅ BrokerManager initialized")
    
    def register_broker(self, pair: str, broker):
        """Register a broker for a pair."""
        self.brokers[pair] = broker
        logger.info(f"   Registered broker: {pair}")
    
    def register_brokers(self, pairs: List[str], brokers: Dict = None):
        """Register multiple brokers."""
        for pair in pairs:
            if pair in brokers:
                self.brokers[pair] = brokers[pair]
                logger.info(f"   Registered broker: {pair}")
            else:
                logger.warning(f"   ⚠️ No broker for {pair}")
    
    def get_decision(self, market_data: Dict) -> Dict:
        """
        Complete hierarchical decision flow:
        Pair Broker → Dollar Engine → Monte Carlo → Execution
        """
        results = {}
        
        for pair, broker in self.brokers.items():
            # ============================================================
            # LEVEL 1: PAIR BROKER
            # ============================================================
            broker_result = broker.analyze(market_data)
            signal = broker_result.get('vote', 'HOLD')
            confidence = broker_result.get('confidence', 0)
            
            if signal == 'HOLD':
                results[pair] = {'signal': 'HOLD', 'confidence': 0, 'passed_levels': 0}
                continue
            
            # ============================================================
            # LEVEL 2: DOLLAR ENGINE (Macro Filter)
            # ============================================================
           
        # ============================================================
        # LEVEL 2: DOLLAR ENGINE FILTER (MACRO CHECK)
        # ============================================================
            gear_type = getattr(broker, 'gear_type', 'INVERSE')
            aligned = self._check_engine_alignment(signal, gear_type, engine_direction)
            
            if not aligned:
                logger.debug(f"⏸️ {pair}: Signal {signal} rejected by Dollar Engine")
                results[pair] = {'signal': 'HOLD', 'confidence': 0, 'reason': 'Engine misalignment'}
                continue
            
            # Boost confidence if aligned
            if engine_direction == 'FORWARD':
                confidence = min(95, confidence + 5)
            elif engine_direction == 'BACKWARD':
                confidence = min(95, confidence + 5)
            
            # ============================================================
            # LEVEL 3: MONTE CARLO (Probability Check)
            # ============================================================
            price = market_data.get(pair, 0)
            if self.monte_carlo and price > 0:
                mc_result = self.monte_carlo.simulate_entry(
                    current_price=price,
                    direction=signal,
                    volatility=0.008 if 'JPY' in pair else 0.005
                )
                mc_confidence = mc_result.get('entry_confidence', 0)
            else:
                mc_confidence = 70  # Default if no MC
            
            if mc_confidence < 50:
                results[pair] = {'signal': 'HOLD', 'confidence': 0, 'passed_levels': 2}
                continue
            
            # Combine confidence
            combined_confidence = (confidence * 0.4 + mc_confidence * 0.6)
            
            # ============================================================
            # FINAL DECISION
            # ============================================================
            if combined_confidence >= 60:
                # Calculate position size
                position_size = broker.calculate_position_size(
                    combined_confidence,
                    broker_result.get('volatility', 0.01),
                    10000
                )
                
                # Calculate SL/TP
                sl_tp = broker.calculate_sl_tp(
                    price,
                    signal,
                    broker_result.get('volatility', 0.01)
                )
                
                results[pair] = {
                    'signal': signal,
                    'confidence': combined_confidence,
                    'position_size': position_size,
                    'sl': sl_tp['sl'],
                    'tp': sl_tp['tp'],
                    'sl_pips': sl_tp['sl_pips'],
                    'tp_pips': sl_tp['tp_pips'],
                    'passed_levels': 4,
                    'broker_result': broker_result,
                    'engine_confirmed': engine_confirmed['confirmed'],
                    'mc_confidence': mc_confidence,
                    'price': price
                }
            else:
                results[pair] = {'signal': 'HOLD', 'confidence': 0, 'passed_levels': 3}
        
        return results
    
    def _check_engine_alignment(self, pair: str, signal: str, market_data: Dict) -> Dict:
        """Check if signal aligns with Dollar Engine."""
        engine_state = market_data.get('engine_state', {})
        engine_direction = engine_state.get('engine_direction', 'NEUTRAL')
        
        broker = self.brokers.get(pair)
        if not broker:
            return {'confirmed': True, 'adjusted_confidence': 50, 'reason': 'No broker'}
        
        gear_type = getattr(broker, 'gear_type', 'INVERSE')
        
        if gear_type == 'INVERSE':
            if signal == 'BUY' and engine_direction == 'FORWARD':
                return {'confirmed': False, 'adjusted_confidence': 0, 'reason': 'BUY against USD strength'}
            elif signal == 'SELL' and engine_direction == 'BACKWARD':
                return {'confirmed': False, 'adjusted_confidence': 0, 'reason': 'SELL against USD weakness'}
            else:
                return {'confirmed': True, 'adjusted_confidence': 75, 'reason': 'Aligned'}
        
        elif gear_type == 'DIRECT':
            if signal == 'BUY' and engine_direction == 'BACKWARD':
                return {'confirmed': False, 'adjusted_confidence': 0, 'reason': 'BUY against USD weakness'}
            elif signal == 'SELL' and engine_direction == 'FORWARD':
                return {'confirmed': False, 'adjusted_confidence': 0, 'reason': 'SELL against USD strength'}
            else:
                return {'confirmed': True, 'adjusted_confidence': 75, 'reason': 'Aligned'}
        
        return {'confirmed': True, 'adjusted_confidence': 50, 'reason': 'No alignment check'}
    
    def get_broker_status(self) -> Dict:
        """Get status of all brokers."""
        status = {}
        for pair, broker in self.brokers.items():
            status[pair] = {
                'signal': getattr(broker, 'signal', 'HOLD'),
                'confidence': getattr(broker, 'confidence', 0),
                'z_score': getattr(broker, 'z_score', 0),
                'persistence': getattr(broker, 'persistence', 0),
            }
        return status