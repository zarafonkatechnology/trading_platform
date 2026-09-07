"""
Filter Data Manager - Save and load filter data from JSON files
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FilterDataManager:
    """Manage filter data persistence"""
    
    def __init__(self, data_dir: str = 'filter_data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # File paths
        self.zscore_file = os.path.join(data_dir, 'zscore_history.json')
        self.volume_file = os.path.join(data_dir, 'volume_history.json')
        self.trend_file = os.path.join(data_dir, 'trend_history.json')
        self.sr_file = os.path.join(data_dir, 'sr_history.json')
        self.news_file = os.path.join(data_dir, 'news_events.json')
        self.metadata_file = os.path.join(data_dir, 'metadata.json')
        
        logger.info(f'✅ FilterDataManager initialized (dir: {data_dir})')
    
    # ===== Z-SCORE HISTORY =====
    def save_zscore_history(self, engine) -> bool:
        """Save Z-Score history"""
        if not hasattr(engine, 'price_history'):
            return False
            
        data = {}
        for symbol, history in engine.price_history.items():
            data[symbol] = list(history)
        
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'symbols': len(data),
            'lookback': getattr(engine, 'lookback', 50),
            'samples': sum(len(h) for h in data.values())
        }
        
        try:
            with open(self.zscore_file, 'w') as f:
                json.dump(data, f, indent=2)
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f'✅ Saved Z-Score history: {len(data)} symbols, {metadata["samples"]} samples')
            return True
        except Exception as e:
            logger.error(f'❌ Failed to save Z-Score history: {e}')
            return False
    
    def load_zscore_history(self, engine) -> bool:
        """Load Z-Score history"""
        try:
            if os.path.exists(self.zscore_file):
                with open(self.zscore_file, 'r') as f:
                    data = json.load(f)
                
                count = 0
                for symbol, history in data.items():
                    for price in history:
                        engine.update_price(symbol, price)
                        count += 1
                
                if os.path.exists(self.metadata_file):
                    with open(self.metadata_file, 'r') as f:
                        metadata = json.load(f)
                    logger.info(f'✅ Loaded Z-Score: {len(data)} symbols, {count} samples (from {metadata.get("timestamp", "unknown")})')
                else:
                    logger.info(f'✅ Loaded Z-Score: {len(data)} symbols, {count} samples')
                return True
        except Exception as e:
            logger.warning(f'⚠️ Failed to load Z-Score history: {e}')
        return False
    
    # ===== VOLUME HISTORY =====
    def save_volume_history(self, filter_obj) -> bool:
        """Save Volume history"""
        if not hasattr(filter_obj, 'volume_history'):
            return False
            
        data = {}
        for symbol, history in filter_obj.volume_history.items():
            data[symbol] = list(history)
        
        try:
            with open(self.volume_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f'✅ Saved Volume history: {len(data)} symbols')
            return True
        except Exception as e:
            logger.error(f'❌ Failed to save Volume history: {e}')
            return False
    
    def load_volume_history(self, filter_obj) -> bool:
        """Load Volume history"""
        try:
            if os.path.exists(self.volume_file):
                with open(self.volume_file, 'r') as f:
                    data = json.load(f)
                
                count = 0
                for symbol, history in data.items():
                    for volume in history:
                        filter_obj.update_volume(symbol, volume)
                        count += 1
                
                logger.info(f'✅ Loaded Volume history: {len(data)} symbols, {count} samples')
                return True
        except Exception as e:
            logger.warning(f'⚠️ Failed to load Volume history: {e}')
        return False
    
    # ===== TREND HISTORY =====
    def save_trend_history(self, filter_obj) -> bool:
        """Save Trend history"""
        if not hasattr(filter_obj, 'price_history'):
            return False
            
        data = {}
        for symbol, history in filter_obj.price_history.items():
            data[symbol] = list(history)
        
        try:
            with open(self.trend_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f'✅ Saved Trend history: {len(data)} symbols')
            return True
        except Exception as e:
            logger.error(f'❌ Failed to save Trend history: {e}')
            return False
    
    def load_trend_history(self, filter_obj) -> bool:
        """Load Trend history"""
        try:
            if os.path.exists(self.trend_file):
                with open(self.trend_file, 'r') as f:
                    data = json.load(f)
                
                count = 0
                for symbol, history in data.items():
                    for price in history:
                        filter_obj.update_price(symbol, price)
                        count += 1
                
                logger.info(f'✅ Loaded Trend history: {len(data)} symbols, {count} samples')
                return True
        except Exception as e:
            logger.warning(f'⚠️ Failed to load Trend history: {e}')
        return False
    
    # ===== SUPPORT/RESISTANCE HISTORY =====
    def save_sr_history(self, filter_obj) -> bool:
        """Save Support/Resistance history"""
        if not hasattr(filter_obj, 'price_history'):
            return False
            
        data = {}
        for symbol, history in filter_obj.price_history.items():
            data[symbol] = list(history)
        
        try:
            with open(self.sr_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f'✅ Saved S/R history: {len(data)} symbols')
            return True
        except Exception as e:
            logger.error(f'❌ Failed to save S/R history: {e}')
            return False
    
    def load_sr_history(self, filter_obj) -> bool:
        """Load Support/Resistance history"""
        try:
            if os.path.exists(self.sr_file):
                with open(self.sr_file, 'r') as f:
                    data = json.load(f)
                
                count = 0
                for symbol, history in data.items():
                    for price in history:
                        filter_obj.update_price(symbol, price)
                        count += 1
                
                logger.info(f'✅ Loaded S/R history: {len(data)} symbols, {count} samples')
                return True
        except Exception as e:
            logger.warning(f'⚠️ Failed to load S/R history: {e}')
        return False
    
    # ===== NEWS EVENTS =====
    def save_news_events(self, events: Dict) -> bool:
        """Save news events"""
        try:
            with open(self.news_file, 'w') as f:
                json.dump(events, f, indent=2)
            logger.info(f'✅ Saved news events: {len(events)} days')
            return True
        except Exception as e:
            logger.error(f'❌ Failed to save news events: {e}')
            return False
    
    def load_news_events(self) -> Optional[Dict]:
        """Load news events"""
        try:
            if os.path.exists(self.news_file):
                with open(self.news_file, 'r') as f:
                    data = json.load(f)
                logger.info(f'✅ Loaded news events: {len(data)} days')
                return data
        except Exception as e:
            logger.warning(f'⚠️ Failed to load news events: {e}')
        return None
    
    # ===== SAVE/LOAD ALL =====
    def save_all(self, controller) -> bool:
        """Save all filter data"""
        saved = []
        
        if hasattr(controller, 'zscore_engine'):
            if self.save_zscore_history(controller.zscore_engine):
                saved.append('Z-Score')
        
        if hasattr(controller, 'strategy'):
            strategy = controller.strategy
            if hasattr(strategy, 'volume_filter'):
                if self.save_volume_history(strategy.volume_filter):
                    saved.append('Volume')
            if hasattr(strategy, 'trend_filter'):
                if self.save_trend_history(strategy.trend_filter):
                    saved.append('Trend')
            if hasattr(strategy, 'sr_filter'):
                if self.save_sr_history(strategy.sr_filter):
                    saved.append('S/R')
        
        if saved:
            logger.info(f'✅ Saved filter data: {", ".join(saved)}')
            return True
        return False
    
    def load_all(self, controller) -> List[str]:
        """Load all filter data, returns list of loaded components"""
        loaded = []
        
        if hasattr(controller, 'zscore_engine'):
            if self.load_zscore_history(controller.zscore_engine):
                loaded.append('Z-Score')
        
        if hasattr(controller, 'strategy'):
            strategy = controller.strategy
            if hasattr(strategy, 'volume_filter'):
                if self.load_volume_history(strategy.volume_filter):
                    loaded.append('Volume')
            if hasattr(strategy, 'trend_filter'):
                if self.load_trend_history(strategy.trend_filter):
                    loaded.append('Trend')
            if hasattr(strategy, 'sr_filter'):
                if self.load_sr_history(strategy.sr_filter):
                    loaded.append('S/R')
        
        if loaded:
            logger.info(f'✅ Loaded filter data: {", ".join(loaded)}')
        return loaded
    
    def has_data(self) -> bool:
        """Check if any filter data exists"""
        return (os.path.exists(self.zscore_file) or 
                os.path.exists(self.volume_file) or 
                os.path.exists(self.trend_file) or 
                os.path.exists(self.sr_file))