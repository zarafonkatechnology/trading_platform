# src/core/forex_wrapper.py
# Wrapper that safely loads the Forex controller

import sys
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ForexControllerWrapper:
    """Wrapper that safely loads and provides access to the Forex controller"""
    
    _instance = None
    _controller = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ForexControllerWrapper, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._load_controller()
    
    def _load_controller(self):
        """Load the Forex controller with proper paths"""
        try:
            # Add paths
            project_root = Path(__file__).parent.parent.parent
            trading_copy = project_root / "Trading_copy"
            
            for p in [str(project_root), str(trading_copy), str(trading_copy / "core")]:
                if p not in sys.path:
                    sys.path.insert(0, p)
            
            # Try to import
            try:
                from trading_controller2 import ForexTradingController
                self._controller = ForexTradingController
                logger.info("✅ Forex controller loaded via wrapper")
                return
            except ImportError:
                pass
            
            # Try direct file
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "trading_controller2",
                str(trading_copy / "trading_controller2.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._controller = module.ForexTradingController
            logger.info("✅ Forex controller loaded via direct file")
            
        except Exception as e:
            logger.error(f"❌ Failed to load Forex controller: {e}")
            self._controller = None
    
    def get_controller(self, config=None):
        """Get an instance of the Forex controller"""
        if self._controller:
            try:
                return self._controller(config or {})
            except Exception as e:
                logger.error(f"❌ Failed to create Forex controller: {e}")
                return None
        return None
    
    def is_available(self):
        return self._controller is not None

# Create singleton instance
forex_wrapper = ForexControllerWrapper()