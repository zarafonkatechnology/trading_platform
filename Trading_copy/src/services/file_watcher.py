# src/services/file_watcher.py
"""
File watcher service - monitors MT4 file and updates cache
"""

import os
import json
import time
import threading
import logging
from datetime import datetime
from typing import Optional

from src.core.price_cache import price_cache

logger = logging.getLogger(__name__)

class MT4FileWatcher:
    """
    Watches MT4 dashboard file and updates price cache
    """
    
    def __init__(self, file_path: str = None):
        if file_path is None:
            file_path = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
        
        self.file_path = file_path
        self._running = False
        self._thread = None
        self._last_modified = 0
        self._check_interval = 0.5  # Check every 500ms
        
        logger.info(f"📁 MT4FileWatcher initialized: {file_path}")
    
    def start(self):
        """Start watching for file changes"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info("✅ MT4FileWatcher started")
    
    def stop(self):
        """Stop watching"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("⏹️ MT4FileWatcher stopped")
    
    def _watch_loop(self):
        """Main watch loop"""
        while self._running:
            try:
                self._check_file()
            except Exception as e:
                logger.debug(f"File watch error: {e}")
            
            time.sleep(self._check_interval)
    
    def _check_file(self):
        """Check if file has been modified"""
        try:
            if not os.path.exists(self.file_path):
                return
            
            # Check modification time
            current_mtime = os.path.getmtime(self.file_path)
            if current_mtime == self._last_modified:
                return
            
            self._last_modified = current_mtime
            
            # Read and parse file
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            # Extract prices
            prices = {}
            if 'prices' in data:
                prices = data['prices']
            else:
                # Try direct keys
                for key, value in data.items():
                    if key not in ['balance', 'equity', 'margin', 'timestamp', 'stats']:
                        if isinstance(value, (int, float)) and value > 0:
                            prices[key] = float(value)
            
            # Also check for account data
            account_data = {
                'balance': data.get('balance', 0),
                'equity': data.get('equity', 0),
                'margin': data.get('margin', 0),
                'free_margin': data.get('free_margin', 0),
            }
            
            # Update cache
            if prices:
                price_cache.update_prices(prices, source="mt4_file")
                logger.debug(f"📊 Updated {len(prices)} prices from MT4 file")
            
        except json.JSONDecodeError:
            pass  # File might be partially written
        except Exception as e:
            logger.debug(f"File check error: {e}")

# Singleton instance
_file_watcher = None

def get_file_watcher():
    global _file_watcher
    if _file_watcher is None:
        _file_watcher = MT4FileWatcher()
    return _file_watcher