# src/mt4_gateway/mt4_connector.py
"""
MT4 Connector - Handles connection to MetaTrader 4
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from src.mt4_gateway.mt4_bridge import MT4Bridge

logger = logging.getLogger(__name__)

class MT4Connector:
    """MT4 Connector for MetaTrader 4 integration"""
    
    def __init__(self, terminal_path: str = None, data_path: str = None):
        self.terminal_path = terminal_path or "C:/Program Files/MetaTrader 4/terminal64.exe"
        self.data_path = data_path or "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/"
        self.is_connected = False
        self.process = None
        self.bridge = MT4Bridge()
        
        logger.info(f"MT4 Connector initialized with terminal: {self.terminal_path}")
    
    async def connect(self, account: str = None, password: str = None, server: str = None) -> bool:
        """Connect to MT4 terminal"""
        try:
            # Check if terminal exists
            if not os.path.exists(self.terminal_path):
                logger.error(f"MT4 terminal not found at {self.terminal_path}")
                return False
            
            # Check if already running
            if self.is_connected:
                logger.info("MT4 already connected")
                return True
            
            # Build command
            cmd = [self.terminal_path]
            
            if account:
                cmd.extend([f"/login:{account}"])
            if password:
                cmd.extend([f"/password:{password}"])
            if server:
                cmd.extend([f"/server:{server}"])
            
            # Launch MT4
            logger.info(f"Launching MT4: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Check if process started
            if self.process.poll() is None:
                self.is_connected = True
                logger.info("MT4 connected successfully")
                return True
            else:
                logger.error("MT4 failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to MT4: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from MT4"""
        try:
            if self.process:
                self.process.terminate()
                self.process = None
            self.is_connected = False
            logger.info("MT4 disconnected")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from MT4: {e}")
            return False
    
    def get_prices(self) -> Dict[str, Any]:
        """Get current prices from MT4"""
        return self.bridge.get_all_data().get('prices', {})
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return self.bridge.get_account_info()
    
    def execute_order(self, symbol: str, order_type: str, volume: float,
                     stop_loss: float = 0, take_profit: float = 0,
                     comment: str = "") -> bool:
        """Execute a trade order"""
        return self.bridge.execute_order(symbol, order_type, volume, stop_loss, take_profit, comment)
    
    def close_order(self, ticket: int) -> bool:
        """Close an open order"""
        return self.bridge.close_order(ticket)
    
    def modify_order(self, ticket: int, stop_loss: float, take_profit: float) -> bool:
        """Modify an existing order"""
        return self.bridge.modify_order(ticket, stop_loss, take_profit)