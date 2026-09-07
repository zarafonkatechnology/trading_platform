# ============================================================
# market_maker_protection.py - Unified Protection System
# ============================================================
# Combines all four detectors into one system
# ============================================================

from .stop_hunt_detector import StopHuntDetector
from .liquidity_sweep import LiquiditySweepDetector
from .volume_profile import VolumeProfile
from .execution_quality import ExecutionQualityMonitor
from typing import Dict, List, Optional
import logging
from datetime import datetime 
logger = logging.getLogger(__name__)


class MarketMakerProtection:
    """
    Unified system to detect and avoid market maker traps.
    """
    
    def __init__(self):
        self.stop_hunt = StopHuntDetector()
        self.liquidity_sweep = LiquiditySweepDetector()
        self.volume_profile = VolumeProfile()
        self.execution_quality = ExecutionQualityMonitor()
        
        self.protection_levels = {
            'STOP_HUNT_ACTIVE': False,
            'LIQUIDITY_SWEEP_ACTIVE': False,
            'LOW_VOLUME_NODE': False,
            'EXECUTION_QUALITY': 'GOOD'
        }
        
        self.last_analysis = None
        
        logger.info("✅ MarketMakerProtection initialized")
    
    def analyze_market(self, symbol: str, candles: List[Dict], price: float, volume: float = None) -> Dict:
        """
        Complete market analysis with all detectors.
        """
        results = {}
        
        # ===== 1. STOP HUNT ANALYSIS =====
        if candles:
            stop_hunt_result = self.stop_hunt.analyze_candle(candles[-1])
            results['stop_hunt'] = stop_hunt_result
        
        # ===== 2. LIQUIDITY SWEEP ANALYSIS =====
        if candles and len(candles) > 5:
            prices = [c['close'] for c in candles[-10:]]
            volumes = [c.get('volume', 0) for c in candles[-10:]]
            
            # Add key levels from volume profile
            volume_result = self.volume_profile.analyze_profile(candles[-50:])
            if volume_result.get('status') != 'INSUFFICIENT_DATA':
                # Add POC and value area as levels
                if 'poc' in volume_result:
                    self.liquidity_sweep.add_level(volume_result['poc'], 'POC')
                if 'value_area_low' in volume_result:
                    self.liquidity_sweep.add_level(volume_result['value_area_low'], 'VALUE_AREA_LOW')
                if 'value_area_high' in volume_result:
                    self.liquidity_sweep.add_level(volume_result['value_area_high'], 'VALUE_AREA_HIGH')
            
            sweep_result = self.liquidity_sweep.analyze_price_action(prices, volumes)
            results['liquidity_sweep'] = sweep_result
        
        # ===== 3. VOLUME PROFILE ANALYSIS =====
        if candles and len(candles) > 10:
            volume_result = self.volume_profile.analyze_profile(candles[-50:])
            results['volume_profile'] = volume_result
        
        # ===== 4. EXECUTION QUALITY =====
        exec_stats = self.execution_quality.get_stats()
        results['execution_quality'] = exec_stats
        
        # ===== 5. OVERALL PROTECTION STATUS =====
        is_safe = True
        warnings = []
        
        # Check stop hunt
        if results.get('stop_hunt', {}).get('is_hunt', False):
            is_safe = False
            warnings.append("Stop hunt detected")
            self.protection_levels['STOP_HUNT_ACTIVE'] = True
        else:
            self.protection_levels['STOP_HUNT_ACTIVE'] = False
        
        # Check liquidity sweep
        if results.get('liquidity_sweep', {}).get('is_sweep', False):
            is_safe = False
            warnings.append("Liquidity sweep detected")
            self.protection_levels['LIQUIDITY_SWEEP_ACTIVE'] = True
        else:
            self.protection_levels['LIQUIDITY_SWEEP_ACTIVE'] = False
        
        # Check low volume node
        volume_context = self.volume_profile.get_price_context(price)
        if volume_context.get('context') == 'LOW_VOLUME_NODE':
            is_safe = False
            warnings.append("Price in low volume node (vacuum zone)")
            self.protection_levels['LOW_VOLUME_NODE'] = True
        else:
            self.protection_levels['LOW_VOLUME_NODE'] = False
        
        # Check execution quality
        if exec_stats.get('quality_breakdown', {}).get('POOR', 0) > 3:
            warnings.append("Poor execution quality detected")
            self.protection_levels['EXECUTION_QUALITY'] = 'POOR'
        else:
            self.protection_levels['EXECUTION_QUALITY'] = 'GOOD'
        
        # ===== 6. BUILD RESULT =====
        result = {
            'is_safe': is_safe,
            'warnings': warnings,
            'protection_levels': self.protection_levels,
            'recommendation': 'HOLD' if not is_safe else 'TRADE',
            'details': results,
            'timestamp': datetime.now().isoformat()
        }
        
        self.last_analysis = result
        
        if not is_safe:
            logger.info(f"🛡️ PROTECTION ACTIVE: {', '.join(warnings)}")
        else:
            logger.debug("✅ All protection checks passed")
        
        return result
    
    def get_status(self) -> Dict:
        """Get current protection status."""
        return {
            'protection_levels': self.protection_levels,
            'is_active': any(self.protection_levels.values()),
            'last_analysis': self.last_analysis
        }
    
    def get_execution_quality(self) -> Dict:
        """Get execution quality stats."""
        return self.execution_quality.get_stats()