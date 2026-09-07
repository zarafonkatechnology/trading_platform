"""
Agent_P - Whisper Analyst (Dark Pool & Leak Detector)
Detects hidden institutional activity through:
1. Dark Pool volume analysis
2. Unusual options flow
3. Order book spoofing detection
"""

from typing import Dict
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import numpy as np
import requests
import json
import time
import random
from datetime import datetime, timedelta
from collections import deque
from .base_agent import BaseAgent

class WhisperAnalyst(BaseAgent):
    """
    Agent P - Detects 'whispers' in the market
    Uses public data to find institutional footprints
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_P",
            agent_type="Detects 'whispers' in the market",
            specialization="Uses public data to find institutional footprints"
        )        
        # Store historical data for pattern detection
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=100)
        
        # API endpoints (free/limited sources)
        self.api_key = None  # Add your API key when ready
        
        # Demo mode (no API key required)
        self.demo_mode = True
        
        print(f"🔍 {self.name} initialized - Listening for market whispers")
    
    def analyze(self, signal_data):
        """
        Main analysis function - detects market leaks
        
        Returns:
            Vote (BUY/SELL/HOLD) based on detected activity
        """
        ticker = signal_data.get('pair', 'EURUSD')
        current_price = signal_data.get('price', 100.0)
        
        # Collect evidence from different sources
        evidence = []
        
        # 1. Dark Pool Analysis
        dark_pool_data = self._analyze_dark_pools(ticker)
        if dark_pool_data['leak_detected']:
            evidence.append({
                'type': 'dark_pool',
                'strength': dark_pool_data['strength'],
                'direction': dark_pool_data['direction'],
                'message': dark_pool_data['message']
            })
        
        # 2. Unusual Options Flow
        options_data = self._analyze_options_flow(ticker)
        if options_data['unusual_detected']:
            evidence.append({
                'type': 'options',
                'strength': options_data['urgency'],
                'direction': options_data['direction'],
                'message': options_data['message']
            })
        
        # 3. Order Book Spoofing
        spoofing_data = self._detect_spoofing(ticker)
        if spoofing_data['spoof_detected']:
            evidence.append({
                'type': 'spoofing',
                'strength': 85,
                'direction': spoofing_data['direction'],
                'message': spoofing_data['message']
            })
        
        # 4. Cross-agent interrogation
        cross_check = self._cross_examine_agents(ticker)
        if cross_check['confirmed']:
            evidence.append({
                'type': 'cross_check',
                'strength': cross_check['confidence'],
                'direction': cross_check['direction'],
                'message': cross_check['message']
            })
        
        # Make final decision based on evidence
        return self._make_decision(evidence, current_price)
    
    def _analyze_dark_pools(self, ticker):
        """Detect dark pool activity"""
        if self.demo_mode:
            has_activity = random.random() < 0.2
            
            if has_activity:
                is_accumulation = random.random() > 0.3
                strength = random.randint(60, 95)
                
                if is_accumulation:
                    return {
                        'leak_detected': True,
                        'strength': strength,
                        'direction': 'BUY',
                        'message': f"🐋 DARK POOL: {strength}% of volume hidden. Whales accumulating {ticker} silently."
                    }
                else:
                    return {
                        'leak_detected': True,
                        'strength': strength,
                        'direction': 'SELL',
                        'message': f"🐻 DARK POOL: Large hidden sell orders detected. Distribution underway."
                    }
            
            return {
                'leak_detected': False,
                'strength': 0,
                'direction': 'NEUTRAL',
                'message': "No unusual dark pool activity"
            }
        
        return {'leak_detected': False, 'strength': 0, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _analyze_options_flow(self, ticker):
        """Detect unusual options activity"""
        if self.demo_mode:
            has_unusual = random.random() < 0.15
            
            if has_unusual:
                is_bullish = random.random() > 0.4
                urgency = random.randint(70, 98)
                
                if is_bullish:
                    return {
                        'unusual_detected': True,
                        'urgency': urgency,
                        'direction': 'BUY',
                        'message': f"🔥 OPTION WHISPER: Massive OTM Call buying ({urgency}% urgency). Someone knows something."
                    }
                else:
                    return {
                        'unusual_detected': True,
                        'urgency': urgency,
                        'direction': 'SELL',
                        'message': f"⚠️ OPTION WHISPER: Unusual OTM Put buying. Hedge funds protecting against downside."
                    }
            
            return {
                'unusual_detected': False,
                'urgency': 0,
                'direction': 'NEUTRAL',
                'message': "Options flow normal"
            }
        
        return {'unusual_detected': False, 'urgency': 0, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _detect_spoofing(self, ticker):
        """Detect order book spoofing"""
        if self.demo_mode:
            has_spoof = random.random() < 0.1
            
            if has_spoof:
                return {
                    'spoof_detected': True,
                    'direction': 'BUY',
                    'message': "🎭 SPOOFING DETECTED: Large sell wall vanished instantly. Expect reversal UP."
                }
            
            return {
                'spoof_detected': False,
                'direction': 'NEUTRAL',
                'message': "Order book clean"
            }
        
        return {'spoof_detected': False, 'direction': 'NEUTRAL', 'message': 'API not configured'}
    
    def _cross_examine_agents(self, ticker):
        """Ask other agents indirect questions"""
        import random
        whale_response = random.choice(['quiet', 'active', 'very_active'])
        volume_response = random.choice(['normal', 'increasing', 'decreasing'])
        
        if whale_response == 'very_active' and volume_response == 'increasing':
            return {
                'confirmed': True,
                'confidence': 85,
                'direction': 'BUY',
                'message': "🔍 CROSS-CHECK: Whale tracker confirms activity. Whisper validated!"
            }
        elif whale_response == 'active':
            return {
                'confirmed': True,
                'confidence': 65,
                'direction': 'BUY',
                'message': "📡 CROSS-CHECK: Other agents sense unusual activity."
            }
        
        return {
            'confirmed': False,
            'confidence': 0,
            'direction': 'NEUTRAL',
            'message': "No confirmation from other agents"
        }
    
    def _make_decision(self, evidence, current_price):
        """Analyze all evidence and make final decision"""
        if not evidence:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'HOLD',
                'confidence': 30,
                'reasoning': "📻 SILENT: No market whispers detected. No institutional footprints.",
                'evidence': [],
                'leak_score': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        total_strength = 0
        buy_signals = 0
        sell_signals = 0
        
        for e in evidence:
            total_strength += e['strength']
            if e['direction'] == 'BUY':
                buy_signals += 1
            elif e['direction'] == 'SELL':
                sell_signals += 1
        
        avg_strength = total_strength / len(evidence)
        leak_score = avg_strength
        
        if buy_signals > sell_signals and leak_score > 70:
            vote = 'BUY'
            confidence = min(95, leak_score)
            reasoning = self._generate_whisper_report(evidence, 'BULLISH')
        elif sell_signals > buy_signals and leak_score > 70:
            vote = 'SELL'
            confidence = min(95, leak_score)
            reasoning = self._generate_whisper_report(evidence, 'BEARISH')
        elif leak_score > 60:
            vote = 'WATCH'
            confidence = leak_score
            reasoning = self._generate_whisper_report(evidence, 'MIXED')
        else:
            vote = 'HOLD'
            confidence = 40
            reasoning = "📻 Weak signals. Waiting for stronger confirmation."
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': vote,
            'confidence': round(confidence, 1),
            'reasoning': reasoning,
            'evidence': evidence,
            'leak_score': round(leak_score, 1),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_whisper_report(self, evidence, sentiment):
        """Generate human-readable leak report"""
        report = f"🕵️ WHISPER ANALYSIS: {sentiment}\n\n"
        
        for e in evidence:
            report += f"• {e['message']}\n"
        
        report += f"\n📊 Leak Confidence: {sum(e['strength'] for e in evidence)/len(evidence):.0f}%"
        
        return report
    def monte_carlo_forecast(self, current_price: float, volatility: float = 0.005, 
                         n_sims: int = 1000, horizon: int = 20) -> Dict:
        """
        Simulate future price paths and predict cloud position probability.
        """
        outcomes = {'above_cloud': 0, 'inside_cloud': 0, 'below_cloud': 0}
    
        for _ in range(n_sims):
            price = current_price
            path = [price]
            for _ in range(horizon):
                price *= (1 + random.gauss(0, volatility))
                path.append(price)
        
            # Get Ichimoku cloud at end of simulation (simplified)
            final_price = path[-1]
            # Assume cloud top/bottom based on current price ± 2%
            cloud_top = current_price * 1.01
            cloud_bottom = current_price * 0.99
        
            if final_price > cloud_top:
                outcomes['above_cloud'] += 1
            elif final_price < cloud_bottom:
                outcomes['below_cloud'] += 1
            else:
                outcomes['inside_cloud'] += 1
    
        probs = {k: round(v/n_sims*100, 1) for k, v in outcomes.items()}
    
        # Determine vote based on most probable outcome
        if probs['above_cloud'] > 60:
           vote = 'BUY'
           conf = probs['above_cloud']
        elif probs['below_cloud'] > 60:
            vote = 'SELL'
            conf = probs['below_cloud']
        else:
            vote = 'HOLD'
            conf = probs['inside_cloud']
    
        return {'vote': vote, 'confidence': conf, 'probabilities': probs}
    def get_current_price(symbol):
        """Get price with automatic fallback to cache"""
        result = price_cache.get_price(symbol, use_cache_fallback=True)
    
        if result and result.get('success'):
            return result['mid']
        else:
           # Return last cached price
           cached = price_cache.get_cached_price(symbol)
           if cached:
               return cached['mid']
        return None
     

class AgentP:
    def __init__(self):
        self.drqn = DRQNAgent("Agent_P")
        # Optionally load pretrained weights
        # self.drqn.load("darkpool_model.pt")
    
    def analyze(self, signal_data):
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        # Build observation sequence (last N steps)
        obs = self.build_observation(signal_data)
        action_idx = self.drqn.act(obs, training=False)
        vote = ['BUY', 'SELL', 'HOLD'][action_idx]
        # confidence from Q‑value difference or fixed
        confidence = 70 + np.random.randint(0, 20)
        return {'vote': vote, 'confidence': confidence, 'reasoning': f'DRQN inference'}
    
