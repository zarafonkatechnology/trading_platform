"""
Voice Alert System for Trading Signals
- Text-to-speech for high-confidence trades
- Configurable voice parameters
- Queue system to prevent overlapping alerts
"""

import pyttsx3
import threading
import time
from collections import deque
from datetime import datetime
from typing import Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VoiceAlertConfig:
    """Configuration for voice alerts."""
    # Voice settings
    voice_rate: int = 180      # Words per minute (150-200)
    voice_volume: float = 1.0  # Volume 0.0 to 1.0
    
    # Alert thresholds
    min_confidence_for_voice: float = 85.0  # Only announce >=85% confidence
    min_strength: str = "STRONG"            # Only STRONG signals
    
    # Cooldown between same asset alerts (seconds)
    cooldown_seconds: int = 300  # 5 minutes
    
    # Message templates
    templates = {
        'BUY_STRONG': "Strong buy signal for {asset} at {price}. Confidence {confidence} percent.",
        'SELL_STRONG': "Strong sell signal for {asset} at {price}. Confidence {confidence} percent.",
        'BUY_WEAK': "Weak buy signal for {asset}.",
        'SELL_WEAK': "Weak sell signal for {asset}.",
        'DEGRADATION': "Warning: Trading performance is degrading. Reduce position sizes.",
        'DAILY_LOSS': "Daily loss limit reached. Trading halted for today.",
        'CYCLE_START': "New trading cycle starting. Monitoring {count} assets.",
        'POSITION_OPEN': "Position opened: {action} {asset} at {price}. Size: {size} percent.",
        'POSITION_CLOSE': "Position closed: {action} {asset} at {price}. Profit: {pnl} percent."
    }


class VoiceAlertEngine:
    """
    Text-to-speech engine for trading alerts.
    Runs in background thread to prevent blocking.
    """
    
    def __init__(self, config: Optional[VoiceAlertConfig] = None):
        self.config = config or VoiceAlertConfig()
        self.engine = None
        self.alert_queue = deque()
        self.last_alert_time = {}
        self.is_speaking = False
        self._thread = None
        self._running = False
        
        # Initialize engine
        self._init_engine()
    
    def _init_engine(self):
        """Initialize the TTS engine."""
        try:
            self.engine = pyttsx3.init()
            
            # Get available voices
            voices = self.engine.getProperty('voices')
            
            # Try to select a female voice (usually more pleasant)
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            
            # Set properties
            self.engine.setProperty('rate', self.config.voice_rate)
            self.engine.setProperty('volume', self.config.voice_volume)
            
            logger.info("✅ Voice alert engine initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS engine: {e}")
            self.engine = None
    
    def _speak(self, text: str):
        """Internal method to speak text."""
        if self.engine is None:
            return
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    def _process_queue(self):
        """Process queued alerts in background."""
        while self._running:
            if self.alert_queue and not self.is_speaking:
                self.is_speaking = True
                alert = self.alert_queue.popleft()
                
                # Check cooldown for asset-specific alerts
                asset = alert.get('asset', '')
                if asset:
                    last_time = self.last_alert_time.get(asset, 0)
                    if time.time() - last_time < self.config.cooldown_seconds:
                        self.is_speaking = False
                        continue
                    self.last_alert_time[asset] = time.time()
                
                # Speak the alert
                self._speak(alert['message'])
                self.is_speaking = False
            
            time.sleep(0.1)
    
    def start(self):
        """Start the voice alert engine in background."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
        logger.info("🎙️ Voice alert engine started")
    
    def stop(self):
        """Stop the voice alert engine."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("🔇 Voice alert engine stopped")
    
    def alert(self, message: str, asset: str = "", priority: int = 1):
        """
        Queue a voice alert.
        
        Args:
            message: The message to speak
            asset: Asset symbol (for cooldown)
            priority: 1=high, 2=normal, 3=low
        """
        if not self.engine:
            return
        
        alert = {
            'message': message,
            'asset': asset,
            'priority': priority,
            'timestamp': datetime.now()
        }
        
        # Insert by priority (higher priority first)
        inserted = False
        for i, existing in enumerate(self.alert_queue):
            if existing['priority'] > priority:
                self.alert_queue.insert(i, alert)
                inserted = True
                break
        
        if not inserted:
            self.alert_queue.append(alert)
        
        logger.info(f"🔊 Alert queued: {message[:50]}...")


class TradingVoiceAlerts:
    """
    Specialized voice alerts for trading signals.
    """
    
    def __init__(self, config: Optional[VoiceAlertConfig] = None):
        self.config = config or VoiceAlertConfig()
        self.engine = VoiceAlertEngine(config)
        self.engine.start()
    
    def _should_alert(self, signal: str, confidence: float) -> bool:
        """Determine if alert should be triggered."""
        if confidence < self.config.min_confidence_for_voice:
            return False
        
        if 'STRONG' not in signal and 'STRONG' not in self.config.min_strength:
            return False
        
        return True
    
    def trade_signal(self, asset: str, action: str, confidence: float, 
                     price: float, signal_type: str = "STRONG"):
        """
        Announce a trade signal.
        
        Args:
            asset: Asset symbol (e.g., "GOLD", "EURUSD")
            action: "BUY" or "SELL"
            confidence: Confidence percentage
            price: Current price
            signal_type: "STRONG" or "WEAK"
        """
        if not self._should_alert(signal_type, confidence):
            return
        
        template = self.config.templates.get(
            f"{action}_{signal_type}", 
            f"{signal_type} {action} signal for {asset}"
        )
        
        message = template.format(
            asset=asset,
            price=price,
            confidence=confidence
        )
        
        self.engine.alert(message, asset=asset, priority=1)
    
    def performance_degradation(self, message: str = ""):
        """Alert about performance degradation."""
        msg = message or self.config.templates['DEGRADATION']
        self.engine.alert(msg, priority=2)
    
    def daily_loss_limit(self):
        """Alert when daily loss limit is reached."""
        self.engine.alert(self.config.templates['DAILY_LOSS'], priority=1)
    
    def cycle_start(self, asset_count: int):
        """Alert at start of trading cycle."""
        message = self.config.templates['CYCLE_START'].format(count=asset_count)
        self.engine.alert(message, priority=3)
    
    def position_opened(self, asset: str, action: str, price: float, size_pct: float):
        """Alert when a position is opened."""
        message = self.config.templates['POSITION_OPEN'].format(
            action=action, asset=asset, price=price, size=size_pct
        )
        self.engine.alert(message, asset=asset, priority=1)
    
    def position_closed(self, asset: str, action: str, price: float, pnl_pct: float):
        """Alert when a position is closed."""
        message = self.config.templates['POSITION_CLOSE'].format(
            action=action, asset=asset, price=price, pnl=pnl_pct
        )
        self.engine.alert(message, asset=asset, priority=1)
    
    def custom_alert(self, message: str, asset: str = "", priority: int = 2):
        """Send a custom voice alert."""
        self.engine.alert(message, asset=asset, priority=priority)
    
    def test(self):
        """Test the voice alert system."""
        print("\n🔊 Testing voice alerts...")
        
        self.trade_signal("GOLD", "BUY", 92, 2385.50, "STRONG")
        time.sleep(2)
        
        self.trade_signal("EURUSD", "SELL", 88, 1.0950, "STRONG")
        time.sleep(2)
        
        self.performance_degradation()
        time.sleep(2)
        
        print("✅ Voice alert test complete")


# ============================================================
# Flask Endpoint for Voice Alerts
# ============================================================

def register_voice_endpoints(app, voice_alerts: TradingVoiceAlerts):
    """Register Flask endpoints for voice alerts."""
    
    @app.route('/api/voice/test', methods=['POST'])
    def voice_test():
        """Test voice alerts."""
        voice_alerts.test()
        return jsonify({'success': True, 'message': 'Voice test triggered'})
    
    @app.route('/api/voice/say', methods=['POST'])
    def voice_say():
        """Speak custom message."""
        data = request.json
        message = data.get('message', '')
        asset = data.get('asset', '')
        if message:
            voice_alerts.custom_alert(message, asset)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    
    print("✅ Voice alert endpoints registered")


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("VOICE ALERT SYSTEM - TEST")
    print("=" * 60)
    
    # Create voice alerts
    config = VoiceAlertConfig()
    config.voice_rate = 170  # Slightly slower for clarity
    voice = TradingVoiceAlerts(config)
    
    # Test the system
    voice.test()
    
    # Run a few more tests
    print("\n📢 Additional tests in 3 seconds...")
    time.sleep(3)
    
    voice.position_opened("GOLD", "BUY", 2385.50, 2.5)
    time.sleep(2)
    
    voice.position_closed("GOLD", "BUY", 2392.00, 0.27)
    time.sleep(2)
    
    voice.daily_loss_limit()
    
    print("\n✅ Voice alert system ready")
    print("🎙️ Your computer will now speak trading alerts")
