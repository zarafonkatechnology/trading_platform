# enhanced_dollar_engine.py - Dollar Engine with Liquidity Agent Integration

from dollar_engine import DollarEngine
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedDollarEngine(DollarEngine):
    """
    Enhanced Dollar Engine with Liquidity Agent Integration
    
    This combines USD strength analysis with institutional liquidity detection
    to provide higher confidence signals.
    """
    
    def __init__(self, lookback: int = 20, liquidity_agent=None):
        """
        Initialize Enhanced Dollar Engine
        
        Args:
            lookback: Number of periods for USD strength calculation
            liquidity_agent: ForexLiquidityAgentEnhanced instance
        """
        super().__init__(lookback)
        self.liquidity_agent = liquidity_agent
        self.liquidity_confirmation = {}
        
        logger.info('✅ Enhanced Dollar Engine initialized')
        logger.info(f'   Lookback: {lookback}')
        logger.info(f'   Liquidity Agent: {"✅ Connected" if liquidity_agent else "❌ Not connected"}')
    
    def check_signal(self, symbol: str, signal_action: str) -> Dict:
        """
        Enhanced signal check with liquidity confirmation
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            signal_action: 'BUY' or 'SELL'
        
        Returns:
            Dict with alignment, confidence, and details
        """
        
        # ===== 1. Get Base Dollar Engine Result =====
        base_result = super().check_signal(symbol, signal_action)
        
        # ===== 2. If Dollar Engine says not aligned, return =====
        if not base_result.get('aligned', False):
            return base_result
        
        # ===== 3. Get Liquidity Agent Analysis =====
        if self.liquidity_agent:
            try:
                # Get current price
                price = self._get_current_price(symbol)
                
                # Analyze with liquidity agent
                liquidity_result = self.liquidity_agent.analyze({
                    'symbol': symbol,
                    'price': price,
                    'engine_state': {
                        'engine_speed': self.usd_strength,
                        'engine_direction': self.usd_direction,
                        'engine_health': 100
                    }
                })
                
                liquidity_vote = liquidity_result.get('vote', 'HOLD')
                liquidity_confidence = liquidity_result.get('confidence', 0)
                stop_run = liquidity_result.get('stop_run', {})
                clusters = liquidity_result.get('liquidity_clusters', {})
                monte_carlo = liquidity_result.get('monte_carlo', {})
                
                # ===== 4. Check Stop Run Confirmation =====
                if stop_run.get('in_progress', False) and stop_run.get('engine_aligned', False):
                    stop_direction = stop_run.get('direction', 'HOLD')
                    
                    if stop_direction == signal_action:
                        confidence = min(95, base_result.get('confidence', 70) + 15)
                        return {
                            'aligned': True,
                            'action': signal_action,
                            'confidence': confidence,
                            'usd_direction': self.usd_direction,
                            'usd_strength': self.usd_strength,
                            'message': f"✅ STOP RUN CONFIRMS {signal_action}: {stop_run.get('reason', '')}",
                            'liquidity': {
                                'stop_run': True,
                                'clusters': clusters.get('clusters', []),
                                'nearest_level': clusters.get('nearest', {}),
                                'confidence': liquidity_confidence
                            }
                        }
                
                # ===== 5. Check Liquidity Cluster =====
                if clusters.get('detected', False):
                    nearest = clusters.get('nearest', {})
                    if nearest:
                        distance = nearest.get('distance_pips', 999)
                        
                        # If within 15 pips of key level
                        if distance < 15:
                            level_direction = nearest.get('direction', 'above')
                            
                            if signal_action == 'BUY' and level_direction == 'above':
                                confidence = min(90, base_result.get('confidence', 70) + 10)
                                return {
                                    'aligned': True,
                                    'action': signal_action,
                                    'confidence': confidence,
                                    'usd_direction': self.usd_direction,
                                    'usd_strength': self.usd_strength,
                                    'message': f"✅ LIQUIDITY CLUSTER: BUY at {nearest.get('level', 0):.5f} ({distance:.1f} pips)",
                                    'liquidity': {
                                        'stop_run': False,
                                        'clusters': clusters.get('clusters', []),
                                        'nearest_level': nearest,
                                        'confidence': liquidity_confidence
                                    }
                                }
                            elif signal_action == 'SELL' and level_direction == 'below':
                                confidence = min(90, base_result.get('confidence', 70) + 10)
                                return {
                                    'aligned': True,
                                    'action': signal_action,
                                    'confidence': confidence,
                                    'usd_direction': self.usd_direction,
                                    'usd_strength': self.usd_strength,
                                    'message': f"✅ LIQUIDITY CLUSTER: SELL at {nearest.get('level', 0):.5f} ({distance:.1f} pips)",
                                    'liquidity': {
                                        'stop_run': False,
                                        'clusters': clusters.get('clusters', []),
                                        'nearest_level': nearest,
                                        'confidence': liquidity_confidence
                                    }
                                }
                
                # ===== 6. Monte Carlo Confirmation =====
                mc_vote = monte_carlo.get('vote', 'HOLD')
                mc_confidence = monte_carlo.get('confidence', 0)
                
                if mc_vote == signal_action and mc_confidence > 60:
                    confidence = min(95, base_result.get('confidence', 70) + 5)
                    return {
                        'aligned': True,
                        'action': signal_action,
                        'confidence': confidence,
                        'usd_direction': self.usd_direction,
                        'usd_strength': self.usd_strength,
                        'message': f"✅ MONTE CARLO CONFIRMS: {signal_action} ({mc_confidence:.0f}%)",
                        'liquidity': {
                            'monte_carlo': monte_carlo,
                            'confidence': mc_confidence
                        }
                    }
                
                # ===== 7. No Liquidity Confirmation =====
                # Return base result with slight reduction
                return {
                    'aligned': True,
                    'action': signal_action,
                    'confidence': max(60, base_result.get('confidence', 70) - 5),
                    'usd_direction': self.usd_direction,
                    'usd_strength': self.usd_strength,
                    'message': f"⚠️ {signal_action} not confirmed by liquidity - proceed with caution",
                    'liquidity': {
                        'confirmed': False,
                        'reason': 'No liquidity confirmation'
                    }
                }
                
            except Exception as e:
                logger.warning(f'⚠️ Liquidity agent error: {e}')
                # Fallback to base result
                return base_result
        
        # ===== 8. No Liquidity Agent =====
        return base_result
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol from history"""
        try:
            if symbol in self.price_history and self.price_history[symbol]:
                return self.price_history[symbol][-1]
        except:
            pass
        
        # Fallback prices
        fallback = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.3000,
            'USDJPY': 150.00,
            'AUDUSD': 0.6500,
            'USDCAD': 1.3500,
            'EURGBP': 0.8500,
            'EURJPY': 165.00,
            'GOLD': 2000.00,
            '#DOLLAR_IND': 100.00
        }
        return fallback.get(symbol, 1.0000)
    
    def get_liquidity_status(self, symbol: str) -> Dict:
        """Get liquidity analysis for a symbol"""
        if not self.liquidity_agent:
            return {'available': False, 'reason': 'Liquidity agent not connected'}
        
        try:
            price = self._get_current_price(symbol)
            result = self.liquidity_agent.analyze({
                'symbol': symbol,
                'price': price,
                'engine_state': {
                    'engine_speed': self.usd_strength,
                    'engine_direction': self.usd_direction,
                    'engine_health': 100
                }
            })
            
            return {
                'available': True,
                'symbol': symbol,
                'price': price,
                'vote': result.get('vote', 'HOLD'),
                'confidence': result.get('confidence', 0),
                'stop_run': result.get('stop_run', {}),
                'liquidity_clusters': result.get('liquidity_clusters', {}),
                'monte_carlo': result.get('monte_carlo', {}),
                'reasoning': result.get('reasoning', '')
            }
        except Exception as e:
            return {'available': False, 'reason': str(e)}