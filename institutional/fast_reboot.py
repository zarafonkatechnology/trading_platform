# ============================================================
# fast_reboot.py - Fast Reboot from Disk
# ============================================================
# Saves state every 5 minutes for quick recovery
# ============================================================

import json
import os
import pickle
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class FastReboot:
    """
    Fast reboot from disk.
    Saves state every 5 minutes for quick recovery.
    """
    
    def __init__(self, save_path: str = "trading_state"):
        self.save_path = save_path
        self.save_interval = 300  # 5 minutes
        self.last_save = datetime.now()
        self.state = {}
        self.is_initialized = False
        
        # Create save directory
        os.makedirs(save_path, exist_ok=True)
        
        logger.info(f"✅ FastReboot initialized (save interval: {self.save_interval}s)")
    
    def save_state(self, data: Dict):
        """
        Save current state to disk.
        """
        try:
            timestamp = datetime.now().isoformat()
            state_data = {
                'timestamp': timestamp,
                'data': data,
                'metadata': {
                    'version': '1.0',
                    'symbols': list(data.keys()) if isinstance(data, dict) else []
                }
            }
            
            # Save as JSON
            json_path = os.path.join(self.save_path, 'state.json')
            with open(json_path, 'w') as f:
                json.dump(state_data, f, indent=2, default=str)
            
            # Save as pickle (faster load)
            pickle_path = os.path.join(self.save_path, 'state.pkl')
            with open(pickle_path, 'wb') as f:
                pickle.dump(state_data, f)
            
            self.last_save = datetime.now()
            logger.debug(f"💾 State saved to {json_path}")
            
        except Exception as e:
            logger.warning(f"⚠️ Save state failed: {e}")
    
    def load_state(self) -> Optional[Dict]:
        """
        Load last saved state from disk.
        """
        try:
            # Try pickle first (faster)
            pickle_path = os.path.join(self.save_path, 'state.pkl')
            if os.path.exists(pickle_path):
                with open(pickle_path, 'rb') as f:
                    state_data = pickle.load(f)
                    logger.info(f"✅ State loaded from pickle (age: {self._get_age(state_data)})")
                    return state_data.get('data', {})
            
            # Try JSON
            json_path = os.path.join(self.save_path, 'state.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    state_data = json.load(f)
                    logger.info(f"✅ State loaded from JSON (age: {self._get_age(state_data)})")
                    return state_data.get('data', {})
            
            logger.info("ℹ️ No saved state found")
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Load state failed: {e}")
            return None
    
    def _get_age(self, state_data: Dict) -> str:
        """Get age of saved state."""
        try:
            timestamp = state_data.get('timestamp')
            if timestamp:
                saved_time = datetime.fromisoformat(timestamp)
                elapsed = (datetime.now() - saved_time).seconds
                if elapsed < 60:
                    return f"{elapsed}s ago"
                elif elapsed < 3600:
                    return f"{elapsed//60}m {elapsed%60}s ago"
                else:
                    return f"{elapsed//3600}h {elapsed%3600//60}m ago"
        except:
            pass
        return "unknown"
    
    def should_save(self) -> bool:
        """Check if it's time to save."""
        return (datetime.now() - self.last_save).seconds >= self.save_interval
    
    def get_last_state(self) -> Optional[Dict]:
        """Get last saved state (fast)."""
        return self.load_state()
    
    def get_status(self) -> Dict:
        """Get reboot status."""
        return {
            'save_interval': self.save_interval,
            'last_save': self.last_save.isoformat(),
            'next_save_in': max(0, self.save_interval - (datetime.now() - self.last_save).seconds),
            'save_path': self.save_path,
            'is_initialized': self.is_initialized
        }