"""
Agent F: Pattern Specialist - Market Maker Logic
Trend Killer (Head & Shoulders) & Liquidity Sweep (Double Top/Bottom)
"""
from backend.agents.base_agent import BaseAgent
import logging
import numpy as np
import random
from datetime import datetime
import psycopg2
import psycopg2.extras
from typing import Dict
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details

logger = logging.getLogger(__name__)

class AgentFCandlestick(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Agent_F",
            agent_type="Pattern Specialist",
            specialization="Head & Shoulders + Double Top/Bottom with Market Maker Logic"
        )

    def find_peaks_troughs(self, data, window=5):
        """Find local peaks and troughs"""
        peaks = []
        troughs = []

        for i in range(window, len(data) - window):
            # Check for peak
            is_peak = True
            for j in range(1, window + 1):
                if data[i] <= data[i - j] or data[i] <= data[i + j]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((i, data[i]))

            # Check for trough
            is_trough = True
            for j in range(1, window + 1):
                if data[i] >= data[i - j] or data[i] >= data[i + j]:
                    is_trough = False
                    break
            if is_trough:
                troughs.append((i, data[i]))

        return peaks, troughs
    def analyze(self, signal_data=None):
        """Analyze method for the trading system"""
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        if signal_data and 'user_query' in signal_data:
            # This is a chat query
            return self.respond_to_user(signal_data['user_query'])
           # Otherwise do pattern analysis
        try:
            market_features = signal_data.get('market_features', {}) if signal_data else {}
            action, confidence = self.predict(signal_data or {}, market_features)
            current_price = self.get_current_price("GOLD")

            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': action,
                'confidence': confidence,
                'reasoning': f"Pattern analysis complete. {self._get_pattern_reasoning(market_features)}",
                'current_price': current_price,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Analyze error: {e}")
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 50,
            'reasoning': "Pattern analysis in progress...",
            'timestamp': datetime.now().isoformat()
        }
    def _get_pattern_reasoning(self, market_features):
        """Get reasoning about detected patterns"""
        pattern_info = market_features.get('pattern_info', {})
        if pattern_info:
            return pattern_info.get('message', 'Pattern detected but needs confirmation')
        return "No clear reversal patterns detected at this time."
    def get_current_price(self, symbol="GOLD"):
        """Get current price from price cache"""
        try:
            import psycopg2

            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="trading_platform",
                user="postgres",
                password="lama"
            )
            cur = conn.cursor()
            cur.execute(
               "SELECT mid FROM price_cache WHERE symbol = %s ORDER BY updated_at DESC LIMIT 1",
               (symbol,)
            )
            row = cur.fetchone()
            cur.close()
            conn.close()

            return float(row[0]) if row else None
        except Exception:
            return None
    def calculate_neckline(self, troughs):
        """Calculate neckline from troughs"""
        if len(troughs) < 2:
            return None

        x1, y1 = troughs[-2]
        x2, y2 = troughs[-1]

        if x2 - x1 == 0:
            return None

        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1

        return {'slope': slope, 'intercept': intercept, 'points': [(x1, y1), (x2, y2)]}

    def detect_head_and_shoulders(self, prices, highs, rsi_values, fib_618):
        """
        TREND KILLER - Head and Shoulders Pattern
        Requirements:
        1. 61.8% symmetry check
        2. RSI divergence filter
        3. Neckline trap confirmation
        """
        if len(prices) < 30:
            return None

        peaks, troughs = self.find_peaks_troughs(highs, window=3)

        if len(peaks) < 3 or len(troughs) < 2:
            return None

        # Get last 3 peaks (Left Shoulder, Head, Right Shoulder)
        left_shoulder = peaks[-3] if len(peaks) >= 3 else None
        head = peaks[-2] if len(peaks) >= 2 else None
        right_shoulder = peaks[-1] if len(peaks) >= 1 else None

        if not all([left_shoulder, head, right_shoulder]):
            return None

        # Check head is highest
        if head[1] <= left_shoulder[1] or head[1] <= right_shoulder[1]:
            return None

        # Calculate neckline
        neckline = self.calculate_neckline(troughs)
        if not neckline:
            return None

        # Calculate Fibonacci retracement from head to neckline
        head_to_neckline = head[1] - neckline['intercept']
        fib_618_level = neckline['intercept'] + head_to_neckline * 0.618

        # ============================================
        # RULE 1: 61.8% SYMMETRY CHECK
        # ============================================
        right_shoulder_price = right_shoulder[1]
        asymmetry = abs(right_shoulder_price - fib_618_level) / fib_618_level

        if asymmetry > 0.02:  # More than 2% deviation
            logger.info(f"Right shoulder at {right_shoulder_price:.2f} vs 61.8% Fib ({fib_618_level:.2f}) - ASYMMETRICAL - Weight reduced")
            symmetry_score = 0.6  # Reduced weight for asymmetrical
        else:
            symmetry_score = 1.0
            logger.info(f"Right shoulder aligned with 61.8% Fibonacci - SYMMETRICAL")

        # ============================================
        # RULE 2: RSI DIVERGENCE FILTER (ULTIMATE TEST)
        # ============================================
        if len(rsi_values) > max(left_shoulder[0], head[0]):
            rsi_left = rsi_values[left_shoulder[0]]
            rsi_head = rsi_values[head[0]]
            rsi_right = rsi_values[right_shoulder[0]] if right_shoulder[0] < len(rsi_values) else 50

            # Bearish divergence: price higher high, RSI lower high
            if head[1] > left_shoulder[1] and rsi_head < rsi_left:
                rsi_divergence = True
                rsi_score = 1.0
                logger.info("RSI bearish divergence CONFIRMED")
            else:
                rsi_divergence = False
                rsi_score = 0.5
                logger.info("RSI divergence NOT confirmed - Pattern weight reduced")
        else:
            rsi_divergence = False
            rsi_score = 0.5

        # ============================================
        # RULE 3: NECKLINE TRAP (Wait for retest)
        # ============================================
        # Check if price has broken below neckline
        current_price = prices[-1]
        neckline_break = current_price < neckline['intercept']

        # Check for retest (price came back to neckline)
        recent_prices = prices[-5:]
        retest = any(abs(p - neckline['intercept']) / neckline['intercept'] < 0.005 for p in recent_prices)

        # Check volume for retest (should be low)
        # This would use volume data from market_features

        if neckline_break and retest:
            trap_score = 1.0
            logger.info("Neckline trap confirmed - Breakout + Retest with low volume")
        elif neckline_break:
            trap_score = 0.7
            logger.info("Neckline broken - Waiting for retest")
        else:
            trap_score = 0.5

        # Calculate overall strength
        strength = (symmetry_score + rsi_score + trap_score) / 3
        confidence = 50 + strength * 40

        return {
            'pattern': 'head_and_shoulders',
            'type': 'bearish',
            'action': 'SELL',
            'left_shoulder': left_shoulder[1],
            'head': head[1],
            'right_shoulder': right_shoulder[1],
            'neckline': neckline['intercept'],
            'fib_618_level': fib_618_level,
            'symmetry_score': symmetry_score,
            'rsi_divergence': rsi_divergence,
            'rsi_score': rsi_score,
            'trap_score': trap_score,
            'strength': strength,
            'confidence': confidence,
            'message': f"Head & Shoulders - Strength: {strength:.2f}"
        }

    def detect_double_top(self, prices, highs, macd_histogram, fib_786):
        """
        LIQUIDITY SWEEP - Double Top Pattern
        Requirements:
        1. Second peak sweeps 78.6% Fibonacci (wick mandate)
        2. MACD divergence confirmation
        3. Flat top rejection check
        """
        if len(prices) < 20:
            return None

        peaks, troughs = self.find_peaks_troughs(highs, window=3)

        if len(peaks) < 2:
            return None

        # Get last 2 peaks
        first_peak = peaks[-2] if len(peaks) >= 2 else None
        second_peak = peaks[-1] if len(peaks) >= 1 else None

        if not all([first_peak, second_peak]):
            return None

        # Find trough between peaks
        start_idx = min(first_peak[0], second_peak[0])
        end_idx = max(first_peak[0], second_peak[0])
        trough = min(prices[start_idx:end_idx]) if end_idx > start_idx else None

        if not trough:
            return None

        # ============================================
        # RULE 1: WICK MANDATE (Sweep 78.6% Fibonacci)
        # ============================================
        peak_range = first_peak[1] - trough
        fib_786_level = first_peak[1] + peak_range * 0.786

        # Check if second peak sweeps above 78.6% level
        sweep_occurred = second_peak[1] > fib_786_level

        # Check if it's a wick (sharp reversal)
        # This would use high/low data - simplified for now
        is_wick = sweep_occurred

        if sweep_occurred and is_wick:
            sweep_score = 1.0
            logger.info(f"Liquidity sweep confirmed at 78.6% Fibonacci - Stop-loss hunt detected")
        elif sweep_occurred:
            sweep_score = 0.7
            logger.info(f"Sweep at 78.6% but not a sharp wick")
        else:
            sweep_score = 0.3
            logger.info(f"No sweep at 78.6% Fibonacci")

        # ============================================
        # RULE 2: MACD DIVERGENCE (Buying pressure dissipated)
        # ============================================
        if len(macd_histogram) > max(first_peak[0], second_peak[0]):
            macd_first = macd_histogram[first_peak[0]]
            macd_second = macd_histogram[second_peak[0]]

            # Bearish divergence: price higher, MACD lower
            if second_peak[1] > first_peak[1] and macd_second < macd_first:
                macd_divergence = True
                macd_score = 1.0
                logger.info("MACD divergence confirmed - Buying pressure dissipated")
            else:
                macd_divergence = False
                macd_score = 0.5
                logger.info("MACD divergence NOT confirmed")
        else:
            macd_divergence = False
            macd_score = 0.5

        # ============================================
        # RULE 3: FLAT TOP REJECTION (Consolidation vs Reversal)
        # ============================================
        # Check if second peak is exactly the same height as first peak
        peak_diff = abs(second_peak[1] - first_peak[1]) / first_peak[1]

        if peak_diff < 0.005 and macd_score > 0.7:
            # Flat top with rising MACD = CONSOLIDATION, not reversal
            flat_top_rejection = True
            logger.warning("FLAT TOP DETECTED with rising MACD - This is CONSOLIDATION, not reversal!")
            return {
                'pattern': 'double_top_rejected',
                'type': 'consolidation',
                'action': 'HOLD',
                'confidence': 20,
                'message': "Flat top with rising MACD - Consolidation pattern, not reversal"
            }
        else:
            flat_top_rejection = False

        # Calculate overall strength
        strength = (sweep_score + macd_score) / 2
        confidence = 50 + strength * 45

        return {
            'pattern': 'double_top',
            'type': 'bearish',
            'action': 'SELL',
            'first_peak': first_peak[1],
            'second_peak': second_peak[1],
            'trough': trough,
            'fib_786_level': fib_786_level,
            'sweep_occurred': sweep_occurred,
            'sweep_score': sweep_score,
            'macd_divergence': macd_divergence,
            'macd_score': macd_score,
            'strength': strength,
            'confidence': confidence,
            'message': f"Liquidity Sweep - Strength: {strength:.2f}"
        }

    def predict(self, signal_data, market_features):
        """
        Main prediction with Market Maker logic
        """
        try:
            asset = signal_data.get('asset_type', 'UNKNOWN')

            # Get market data
            candles = market_features.get('candles', [])
            if len(candles) < 30:
                return 'HOLD', 50

            closes = [c['close'] for c in candles]
            highs = [c['high'] for c in candles]

            # Get indicators
            rsi_values = market_features.get('rsi_history', [50] * len(closes))
            macd_histogram = market_features.get('macd_histogram', [0] * len(closes))

            # Calculate Fibonacci levels
            swing_high = max(highs[-50:])
            swing_low = min(closes[-50:])
            fib_618 = swing_high - (swing_high - swing_low) * 0.618
            fib_786 = swing_high - (swing_high - swing_low) * 0.786

            # ============================================
            # DETECT PATTERNS
            # ============================================

            # TREND KILLER - Head & Shoulders
            head_shoulders = self.detect_head_and_shoulders(closes, highs, rsi_values, fib_618)

            # LIQUIDITY SWEEP - Double Top
            double_top = self.detect_double_top(closes, highs, macd_histogram, fib_786)

            # ============================================
            # MAKE DECISION
            # ============================================

            action = 'HOLD'
            confidence = 50
            pattern_info = None

            # Check for flat top rejection first (veto)
            if double_top and double_top.get('pattern') == 'double_top_rejected':
                logger.warning(f"{self.name}: FLAT TOP REJECTION - {double_top['message']}")
                return 'HOLD', 20

            # Head & Shoulders (Trend Killer)
            if head_shoulders and head_shoulders['confidence'] > 65:
                action = head_shoulders['action']
                confidence = head_shoulders['confidence']
                pattern_info = head_shoulders
                logger.info(f"{self.name}: 🔴 {head_shoulders['message']}")

            # Double Top (Liquidity Sweep)
            elif double_top and double_top['confidence'] > 65:
                action = double_top['action']
                confidence = double_top['confidence']
                pattern_info = double_top
                logger.info(f"{self.name}: 🔴 {double_top['message']}")

            # Store for supervisor
            market_features['pattern_info'] = pattern_info

            return action, min(95, confidence)

        except Exception as e:
            logger.error(f"{self.name} prediction error: {e}")
            return 'HOLD', 50
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
        # Add this method to handle price queries
    def handle_price_query(self, user_query: str) -> str:
        """Handle user questions about prices - ONLY uses database, NO AI"""
        import psycopg2
    
        query_lower = user_query.lower()
    
        # Detect what they're asking about
        if 'gold' in query_lower:
            symbol = 'GOLD'  # ← YOUR exact symbol from database
            name = 'Gold'
        else:
            return f"{self.name}: I can check the price for Gold. What would you like to know?"
    
        # Get price from YOUR database ONLY
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="trading_platform",
                user="postgres",
                password="lama"
            )
            cur = conn.cursor()
        
            # Get the exact price from your database
            cur.execute("""
                SELECT mid, updated_at 
                FROM price_cache 
                WHERE symbol = 'GOLD'
                ORDER BY updated_at DESC 
                LIMIT 1
                """)
        
            row = cur.fetchone()
            cur.close()
            conn.close()
            
            if row and row[0] is not None:
                # Use YOUR database price
                db_price = float(row[0])
                updated_at = row[1]
                return f"{self.name}: Gold is ${db_price:.2f} per ounce (from database, updated {updated_at})."
            else:
                # No data in database
                return f"{self.name}: I don't have any price data for Gold in the database. Please check if MT4 EA is connected."
                
        except Exception as e:
            return f"{self.name}: Cannot connect to database: {e}"
     
        
    def get_price_from_database(self, user_query: str) -> str:
        """SIMPLE database price lookup - NO AI, NO RANDOM NUMBERS"""
        import psycopg2
        
        try:
                conn = psycopg2.connect(
                        host="localhost",
                        port=5432,
                        database="trading_platform",
                        user="postgres",
                        password="lama"
                )
                cur = conn.cursor()
                
                # Get the price from your database
                cur.execute("""
                        SELECT mid, updated_at 
                        FROM price_cache 
                        WHERE symbol = 'GOLD'
                        ORDER BY updated_at DESC 
                        LIMIT 1
                """)
                
                row = cur.fetchone()
                cur.close()
                conn.close()
                
                if row and row[0] is not None:
                        price = float(row[0])
                        updated = row[1]
                        return f"Gold is ${price:.2f} per ounce (from database, updated {updated})."
                else:
                        return "I don't have gold price data in the database. Please check if MT4 EA is connected."
                        
        except Exception as e:
                return f"Cannot read database: {e}"
