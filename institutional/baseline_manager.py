# ============================================================
# baseline_manager.py - Asset-Specific Baselines (UPDATED)
# ============================================================
# Stores unique Z-score distributions for each asset class
# Saves to disk every 5 minutes (configurable)
# ============================================================

import json
import os
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import threading

logger = logging.getLogger(__name__)


class BaselineManager:
    """
    Manages asset-specific baselines for Z-score distributions.
    
    Asset Classes:
        - INDICES: High volatility, wide ranges
        - FOREX: Moderate volatility, tighter ranges
        - COMMODITIES: Variable volatility
        - ENERGY: High volatility, event-driven
        - METALS: Moderate volatility, safe-haven
    
    Save Interval: Every 5 minutes (configurable)
    """
    
    def __init__(self, config_path: str = "baseline_config.json", save_interval_seconds: int = 300):
        """
        Args:
            config_path: Path to save baseline data
            save_interval_seconds: How often to save (default 5 minutes)
        """
        self.config_path = config_path
        self.save_interval_seconds = save_interval_seconds
        self.last_save_time = datetime.now()
        self.dirty = False  # Track if changes need to be saved
        
        self.baselines = {}
        self.asset_classes = {
            '#NASDAQ100': 'INDICES',
            '#S&P500': 'INDICES',
            '#DJ30': 'INDICES',
            'EURUSD': 'FOREX',
            'GBPUSD': 'FOREX',
            'USDJPY': 'FOREX',
            'AUDUSD': 'FOREX',
            'USDCAD': 'FOREX',
            'NZDUSD': 'FOREX',
            'GOLD': 'METALS',
            'SILVER': 'METALS',
            'BRENT_OIL': 'ENERGY',
            'CrudeOIL': 'ENERGY',
        }
        
        # Class-specific requirements
        self.class_requirements = {
            'INDICES': {
                'min_samples': 30,
                'required_volatility': 0.001,
                'expected_z_range': (-3.0, 3.0)
            },
            'FOREX': {
                'min_samples': 25,
                'required_volatility': 0.0005,
                'expected_z_range': (-2.5, 2.5)
            },
            'METALS': {
                'min_samples': 35,
                'required_volatility': 0.002,
                'expected_z_range': (-3.5, 3.5)
            },
            'ENERGY': {
                'min_samples': 40,
                'required_volatility': 0.003,
                'expected_z_range': (-4.0, 4.0)
            }
        }
        
        # Load existing baselines
        self._load_baselines()
        
        # Start auto-save thread
        self._start_auto_save()
        
        logger.info(f"✅ BaselineManager initialized")
        logger.info(f"   Save Interval: {save_interval_seconds}s (every {save_interval_seconds//60} minutes)")
        logger.info(f"   Loaded {len(self.baselines)} existing baselines")
    
    def get_asset_class(self, symbol: str) -> str:
        """Get asset class for symbol."""
        return self.asset_classes.get(symbol, 'FOREX')
    
    def get_class_requirements(self, symbol: str) -> Dict:
        """Get requirements for asset class."""
        asset_class = self.get_asset_class(symbol)
        return self.class_requirements.get(asset_class, self.class_requirements['FOREX'])
    
    def get_min_samples(self, symbol: str) -> int:
        """Get minimum samples required for asset."""
        requirements = self.get_class_requirements(symbol)
        return requirements['min_samples']
    
    def update_baseline(self, symbol: str, z_scores: List[float], spreads: List[float] = None):
        """Update baseline for a symbol."""
        if symbol not in self.baselines:
            self.baselines[symbol] = {
                'asset_class': self.get_asset_class(symbol),
                'z_scores': [],
                'spreads': [],
                'mean': 0,
                'std': 0,
                'samples': 0,
                'last_update': None,
                'first_update': datetime.now().isoformat()
            }
        
        baseline = self.baselines[symbol]
        baseline['z_scores'].extend(z_scores)
        if spreads:
            baseline['spreads'].extend(spreads)
        
        # Keep only last 200 samples
        if len(baseline['z_scores']) > 200:
            baseline['z_scores'] = baseline['z_scores'][-200:]
        if len(baseline['spreads']) > 200:
            baseline['spreads'] = baseline['spreads'][-200:]
        
        # Update statistics
        if len(baseline['z_scores']) >= 10:
            baseline['mean'] = float(np.mean(baseline['z_scores']))
            baseline['std'] = float(np.std(baseline['z_scores']))
            baseline['samples'] = len(baseline['z_scores'])
            baseline['last_update'] = datetime.now().isoformat()
            self.dirty = True  # Mark for saving
        
        # Auto-save if interval passed
        self._auto_save_if_needed()
    
    def get_z_normalized(self, symbol: str, z_score: float) -> float:
        """Get asset-normalized Z-score."""
        if symbol not in self.baselines:
            return z_score
        
        baseline = self.baselines[symbol]
        if baseline['std'] > 0:
            return (z_score - baseline['mean']) / baseline['std']
        return z_score
    
    def get_ready_status(self, symbol: str) -> Dict:
        """Get readiness status for symbol."""
        min_samples = self.get_min_samples(symbol)
        baseline = self.baselines.get(symbol, {'samples': 0, 'mean': 0, 'std': 0})
        
        samples = baseline['samples']
        progress = min(100, (samples / min_samples) * 100)
        
        is_ready = samples >= min_samples
        
        return {
            'symbol': symbol,
            'asset_class': self.get_asset_class(symbol),
            'samples': samples,
            'min_samples': min_samples,
            'progress': round(progress, 1),
            'is_ready': is_ready,
            'mean': baseline.get('mean', 0),
            'std': baseline.get('std', 0),
            'status': '✅ READY' if is_ready else f'⏳ {samples}/{min_samples}'
        }
    
    def get_all_status(self, symbols: List[str]) -> Dict:
        """Get readiness status for all symbols."""
        return {symbol: self.get_ready_status(symbol) for symbol in symbols}
    
    def _auto_save_if_needed(self):
        """Save if interval has passed and data is dirty."""
        if not self.dirty:
            return
        
        elapsed = (datetime.now() - self.last_save_time).seconds
        if elapsed >= self.save_interval_seconds:
            self._save_baselines()
    
    def _load_baselines(self):
        """Load baselines from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.baselines = data.get('baselines', {})
                    logger.info(f"   Loaded {len(self.baselines)} baselines from {self.config_path}")
                    
                    # Check age of saved data
                    timestamp = data.get('timestamp')
                    if timestamp:
                        saved_time = datetime.fromisoformat(timestamp)
                        age = (datetime.now() - saved_time).seconds
                        if age > 3600:
                            logger.warning(f"   ⚠️ Saved baseline is {age//3600}h old")
                        else:
                            logger.info(f"   ✅ Baseline age: {age//60}m {age%60}s")
            except Exception as e:
                logger.warning(f"   Could not load baselines: {e}")
    
    def _save_baselines(self):
        """Save baselines to disk."""
        try:
            # Create backup of existing file
            if os.path.exists(self.config_path):
                backup_path = self.config_path + '.backup'
                try:
                    os.rename(self.config_path, backup_path)
                except:
                    pass
            
            # Save new data
            with open(self.config_path, 'w') as f:
                json.dump({
                    'baselines': self.baselines,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {
                        'version': '1.0',
                        'symbols': list(self.baselines.keys()),
                        'total_samples': sum(b.get('samples', 0) for b in self.baselines.values()),
                        'last_update': datetime.now().isoformat()
                    }
                }, f, indent=2)
            
            self.last_save_time = datetime.now()
            self.dirty = False
            
            logger.info(f"💾 Baselines saved to {self.config_path}")
            logger.info(f"   Symbols: {len(self.baselines)}, Total Samples: {sum(b.get('samples', 0) for b in self.baselines.values())}")
            
        except Exception as e:
            logger.warning(f"   Could not save baselines: {e}")
    
    def _start_auto_save(self):
        """Start auto-save thread."""
        def auto_save_loop():
            while True:
                import time
                time.sleep(self.save_interval_seconds)
                if self.dirty:
                    self._save_baselines()
        
        thread = threading.Thread(target=auto_save_loop, daemon=True)
        thread.start()
        logger.info("   ✅ Auto-save thread started")
    
    def force_save(self):
        """Force save immediately."""
        self._save_baselines()
    
    def force_load(self):
        """Force load from disk."""
        self._load_baselines()
    
    def get_progress_summary(self, symbols: List[str]) -> str:
        """Get a formatted progress summary."""
        statuses = self.get_all_status(symbols)
        
        lines = ["📊 COLD START PROGRESS:"]
        for symbol, status in statuses.items():
            bar = '█' * int(status['progress'] / 5)
            spaces = ' ' * (20 - len(bar))
            lines.append(f"   {symbol:12} [{bar}{spaces}] {status['progress']:.0f}% ({status['status']})")
        
        return "\n".join(lines)
    
    def get_status(self) -> Dict:
        """Get current status."""
        return {
            'total_symbols': len(self.baselines),
            'total_samples': sum(b.get('samples', 0) for b in self.baselines.values()),
            'last_save': self.last_save_time.isoformat(),
            'next_save_in': max(0, self.save_interval_seconds - (datetime.now() - self.last_save_time).seconds),
            'dirty': self.dirty,
            'save_interval_seconds': self.save_interval_seconds
        }