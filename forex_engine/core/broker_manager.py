
# C:\trading_platform\forex_engine\brokers\broker_manager.py

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

class BrokerManager:
    """
    Hierarchical Signal Flow with Dollar Engine Consistency Filter:

    1. Z-SCORE MEAN REVERSION (Primary) - Generates raw signals per pair
    2. DOLLAR ENGINE CONSISTENCY CHECK - Validates signals against USD direction
    3. RL AGENT OVERRIDE (Special) - Needs hybrid when Z not peaked
    4. MONTE CARLO S/R GATE - Blocks bad entries only

    Dollar Engine Role:
    - Calculates overall USD strength from ALL pairs
    - Checks if each signal is CONSISTENT with USD direction
    - If CONSISTENT → Normal confidence
    - If CONTRADICTS → Reduce confidence by 50% or block
    - If NO CLEAR USD direction (mixed market) → Allow all
    """

    def __init__(self, engine, monte_carlo, rl_agent=None, hybrid_coordinator=None):
        self.engine = engine
        self.monte_carlo = monte_carlo
        self.rl_agent = rl_agent
        self.hybrid_coordinator = hybrid_coordinator
        self.brokers: Dict = {}
        self.decision_history = []

        # Z-Score Configuration
        self.z_entry_threshold = 1.5
        self.z_exit_threshold = 0.3
        self.min_persistence = 2

        # Monte Carlo Gate
        self.mc_min_confidence = 25
        self.mc_sr_block_threshold = 0.7

        # Dollar Engine Filter
        self.de_confidence_penalty = 0.5    # Reduce confidence by 50% if contradicts
        self.de_block_threshold = 0.8         # Block if contradiction > 80%

        logger.info("✅ BrokerManager initialized (Hierarchical + Dollar Engine)")

    def register_broker(self, pair: str, broker_class):
        """Register a broker for a pair."""
        try:
            if isinstance(broker_class, type):
                try:
                    broker = broker_class(pair=pair, config={})
                except TypeError:
                    try:
                        broker = broker_class()
                        broker.pair = pair
                    except:
                        from .base_broker import BaseBroker
                        broker = BaseBroker(pair=pair, config={})
                self.brokers[pair] = broker
                logger.info(f"   Registered broker: {pair}")
            else:
                self.brokers[pair] = broker_class
                logger.info(f"   Registered broker instance: {pair}")
        except Exception as e:
            logger.error(f"   ❌ Failed to register broker for {pair}: {e}")
            from .base_broker import BaseBroker
            self.brokers[pair] = BaseBroker(pair=pair, config={})

    def register_brokers(self, pairs: List[str], broker_map: Dict = None):
        """Register multiple brokers."""
        broker_map = broker_map or {}
        for pair in pairs:
            if pair in broker_map:
                self.register_broker(pair, broker_map[pair])
            else:
                logger.warning(f"   ⚠️ No broker class for {pair}, using BaseBroker")
                from .base_broker import BaseBroker
                self.register_broker(pair, BaseBroker)

    # ============================================================
    # CORE: HIERARCHICAL DECISION ENGINE
    # ============================================================

    def get_decision(self, market_data: Dict) -> Dict:
        """
        Get decisions for ALL pairs.

        Flow:
        1. Calculate Dollar Engine state (USD strength from all pairs)
        2. For each pair: check Z-signal, validate against Dollar Engine
        3. If no Z-signal: check RL agent
        4. All signals pass through Monte Carlo S/R gate
        """
        results = {}

        # STEP 1: Calculate Dollar Engine state
        dollar_state = self._calculate_dollar_state(market_data)
        logger.info(f"💵 Dollar Engine: {dollar_state['direction']} "
                   f"(strength={dollar_state['strength']:.2f}, "
                   f"confidence={dollar_state['confidence']:.1f}%)")

        # STEP 2: Get decisions for each pair
        for pair, broker in self.brokers.items():
            try:
                decision = self._get_pair_decision(pair, broker, market_data, dollar_state)
                results[pair] = decision

                if decision.get('signal') != 'HOLD':
                    de_status = decision.get('dollar_engine', {})
                    logger.info(f"   ✅ {pair}: {decision['signal']} "
                              f"(conf={decision['confidence']:.1f}%, "
                              f"source={decision.get('source')}, "
                              f"z={decision.get('z_score', 0):.2f}, "
                              f"DE={de_status.get('status', 'N/A')})")

            except Exception as e:
                logger.error(f"   ❌ Error for {pair}: {e}")
                results[pair] = {'signal': 'HOLD', 'confidence': 0, 
                                'z_score': getattr(broker, 'z_score', 0)}

        self.decision_history.append({'dollar_state': dollar_state, 'decisions': results})
        return results

    def _get_pair_decision(self, pair: str, broker, market_data: Dict, 
                           dollar_state: Dict) -> Dict:
        """Hierarchical decision for single pair with Dollar Engine filter."""

        # Update broker with current price
        price = market_data.get(pair, 0)
        if price > 0:
            broker.current_price = price
            if hasattr(broker, 'close_history'):
                broker.close_history.append(price)

        # Extract raw metrics
        z_score = getattr(broker, 'z_score', 0)
        threshold = getattr(broker, 'entry_threshold', self.z_entry_threshold)

        # Preserve z-score across analyze()
        preserved_z = z_score
        broker_result = broker.analyze(market_data)
        persistence = broker_result.get(
            'persistence',
            getattr(broker, 'persistence', getattr(broker, 'persistence_counter', 0))
        )
        min_persistence = getattr(broker, 'min_persistence', self.min_persistence)
        if preserved_z != 0 and broker_result.get('z_score', 0) == 0:
            broker_result['z_score'] = preserved_z
            broker.z_score = preserved_z
        z_score = broker_result.get('z_score', z_score)

        # ============================================================
        # LEVEL 1: Z-SCORE MEAN REVERSION (PRIMARY)
        # ============================================================
        z_signal = self._check_z_score(pair, z_score, threshold, persistence, min_persistence)

        if z_signal['signal'] != 'HOLD':
            # Check Dollar Engine consistency
            de_check = self._check_dollar_consistency(pair, z_signal['signal'], 
                                                       z_score, dollar_state)

            # Adjust confidence based on Dollar Engine
            adjusted_confidence = z_signal['confidence']
            if de_check['status'] == 'CONTRADICTS':
                adjusted_confidence *= self.de_confidence_penalty
                logger.warning(f"   ⚠️ {pair}: Z-signal CONTRADICTS Dollar Engine "
                             f"(conf reduced: {z_signal['confidence']:.1f}% → {adjusted_confidence:.1f}%)")

                # If contradiction is severe, block
                if de_check['contradiction_strength'] > self.de_block_threshold:
                    return {
                        'signal': 'HOLD',
                        'confidence': adjusted_confidence,
                        'z_score': z_score,
                        'reasoning': f"Z-signal BLOCKED by Dollar Engine: {de_check['reason']}",
                        'source': 'z_score_de_blocked',
                        'layer': 'primary_de_blocked',
                        'dollar_engine': de_check
                    }

            # Monte Carlo gate
            mc = self._monte_carlo_gate(pair, z_signal['signal'], price, market_data, broker_result)

            if mc['allowed']:
                return {
                    'signal': z_signal['signal'],
                    'confidence': adjusted_confidence,
                    'z_score': z_score,
                    'position_size': mc['position_size'],
                    'sl': mc['sl'], 'tp': mc['tp'],
                    'reasoning': f"Z-Score: {z_signal['reasoning']} | "
                               f"DE: {de_check['reason']} | "
                               f"MC: {mc['reasoning']}",
                    'source': 'z_score',
                    'layer': 'primary',
                    'dollar_engine': de_check,
                    'mc_confidence': mc['mc_confidence'],
                    'sr_risk': mc.get('sr_risk', 0)
                }
            else:
                return {
                    'signal': 'HOLD',
                    'confidence': adjusted_confidence,
                    'z_score': z_score,
                    'reasoning': f"Z-signal blocked by MC: {mc['reasoning']}",
                    'source': 'z_score_mc_blocked',
                    'layer': 'primary_mc_blocked',
                    'dollar_engine': de_check
                }

        # ============================================================
        # LEVEL 2: RL AGENT OVERRIDE
        # ============================================================
        rl = self._check_rl(pair, market_data, z_score, threshold)

        if rl['signal'] != 'HOLD':
            # Check Dollar Engine consistency for RL too
            de_check = self._check_dollar_consistency(pair, rl['signal'], 
                                                       z_score, dollar_state)

            if rl['needs_hybrid']:
                if not self._hybrid_confirms(pair, rl['signal'], market_data):
                    return {
                        'signal': 'HOLD',
                        'confidence': rl['confidence'],
                        'z_score': z_score,
                        'reasoning': f"RL rejected: Hybrid disagrees",
                        'source': 'rl_rejected',
                        'layer': 'rl_hybrid_rejected',
                        'dollar_engine': de_check
                    }

            # Monte Carlo gate
            mc = self._monte_carlo_gate(pair, rl['signal'], price, market_data, broker_result)

            if mc['allowed']:
                return {
                    'signal': rl['signal'],
                    'confidence': rl['confidence'],
                    'z_score': z_score,
                    'position_size': mc['position_size'],
                    'sl': mc['sl'], 'tp': mc['tp'],
                    'reasoning': f"RL: {rl['reasoning']} | DE: {de_check['reason']} | MC: {mc['reasoning']}",
                    'source': 'rl_agent',
                    'layer': 'rl_override',
                    'dollar_engine': de_check,
                    'hybrid_confirmed': rl['needs_hybrid']
                }

        # No signal
        return {
            'signal': 'HOLD',
            'confidence': 50,
            'z_score': z_score,
            'reasoning': f"No signal: Z={z_score:.2f}, persist={persistence}/{min_persistence}",
            'source': 'none',
            'layer': 'no_signal',
            'dollar_engine': {'status': 'N/A'}
        }

    # ============================================================
    # DOLLAR ENGINE: USD STRENGTH & CONSISTENCY
    # ============================================================

    def _calculate_dollar_state(self, market_data: Dict) -> Dict:
        """
        Calculate overall USD strength from all pairs.

        Pairs with USD as BASE (USD/XXX): Price UP = USD strong
        Pairs with USD as QUOTE (XXX/USD): Price DOWN = USD strong

        Returns:
        {
            'direction': 'STRONG' | 'WEAK' | 'MIXED',
            'strength': float (0-1),
            'confidence': float (0-100),
            'pair_contributions': Dict[pair, value]
        }
        """
        contributions = {}

        for pair, broker in self.brokers.items():
            price = market_data.get(pair, 0)
            if price <= 0:
                continue

            # Get price change (trend direction)
            if hasattr(broker, 'close_history') and len(broker.close_history) >= 2:
                prev_price = broker.close_history[-2]
                price_change = (price - prev_price) / prev_price
            else:
                price_change = 0

            # Determine if this pair suggests USD strength
            if pair.startswith('USD'):
                # USD is BASE currency (USD/JPY, USD/CHF, USDCAD)
                # Price UP = USD strong
                usd_strength = price_change
            elif pair.endswith('USD'):
                # USD is QUOTE currency (EUR/USD, GBP/USD, AUD/USD, NZD/USD)
                # Price DOWN = USD strong
                usd_strength = -price_change
            else:
                # Cross pair (EUR/GBP, EUR/JPY, etc.) - no direct USD
                # Skip for dollar strength calculation
                continue

            contributions[pair] = usd_strength

        if not contributions:
            return {'direction': 'MIXED', 'strength': 0.5, 'confidence': 0, 
                    'pair_contributions': {}}

        # Calculate average USD strength
        avg_strength = sum(contributions.values()) / len(contributions)

        # Determine direction
        if avg_strength > 0.001:
            direction = 'STRONG'
            strength = min(1.0, avg_strength * 100 + 0.5)
        elif avg_strength < -0.001:
            direction = 'WEAK'
            strength = min(1.0, abs(avg_strength) * 100 + 0.5)
        else:
            direction = 'MIXED'
            strength = 0.5

        # Confidence based on agreement among pairs
        agreement = sum(1 for v in contribufbuytions.values() 
                       if (direction == 'STRONG' and v > 0) or 
                          (direction == 'WEAK' and v < 0) or
                          (direction == 'MIXED' and abs(v) < 0.001))
        confidence = (agreement / len(contributions)) * 100 if contributions else 0

        return {
            'direction': direction,
            'strength': strength,
            'confidence': confidence,
            'pair_contributions': contributions,
            'avg_strength': avg_strength
        }

    def _check_dollar_consistency(self, pair: str, signal: str, z_score: float,
                                   dollar_state: Dict) -> Dict:
        """
        Check if signal is CONSISTENT with Dollar Engine direction.

        Logic:
        - If Dollar Engine says USD STRONG:
          - EUR/USD SELL = CONSISTENT (expects USD to strengthen)
          - USD/JPY BUY = CONSISTENT (expects USD to strengthen)
          - EUR/USD BUY = CONTRADICTS
          - USD/JPY SELL = CONTRADICTS

        - If Dollar Engine says USD WEAK:
          - EUR/USD BUY = CONSISTENT (expects USD to weaken)
          - USD/JPY SELL = CONSISTENT (expects USD to weaken)
          - EUR/USD SELL = CONTRADICTS
          - USD/JPY BUY = CONTRADICTS

        - If MIXED: Always CONSISTENT (no clear direction)
        """
        de_direction = dollar_state.get('direction', 'MIXED')
        de_confidence = dollar_state.get('confidence', 0)

        if de_direction == 'MIXED' or de_confidence < 50:
            return {
                'status': 'CONSISTENT',
                'reason': f"Dollar Engine MIXED or low confidence ({de_confidence:.1f}%) - allowing",
                'contradiction_strength': 0
            }

        # Determine what direction this signal implies for USD
        if pair.startswith('USD'):
            # USD is BASE: BUY = USD strengthens, SELL = USD weakens
            signal_usd_direction = 'STRONG' if signal == 'BUY' else 'WEAK'
        elif pair.endswith('USD'):
            # USD is QUOTE: BUY = USD weakens, SELL = USD strengthens
            signal_usd_direction = 'WEAK' if signal == 'BUY' else 'STRONG'
        else:
            # Cross pair - check if it contains USD indirectly
            # For simplicity, allow cross pairs
            return {
                'status': 'CONSISTENT',
                'reason': f"Cross pair {pair} - no direct USD check",
                'contradiction_strength': 0
            }
            
            
            
            

        # Check consistency
        if signal_usd_direction == de_direction:
            return {
                'status': 'CONSISTENT',
                'reason': f"Signal {signal} aligns with USD {de_direction} "
                         f"(DE confidence: {de_confidence:.1f}%)",
                'contradiction_strength': 0
            }
        else:
            # Calculate contradiction strength
            contradiction = de_confidence / 100.0
            return {
                'status': 'CONTRADICTS',
                'reason': f"Signal {signal} CONTRADICTS USD {de_direction} "
                         f"(expects USD {signal_usd_direction}, DE says {de_direction}, "
                         f"confidence: {de_confidence:.1f}%)",
                'contradiction_strength': contradiction
            }

    # ============================================================
    # LEVEL 1: Z-SCORE SIGNAL
    # ============================================================

    def _check_z_score(self, pair, z_score, threshold, persistence, min_persistence):
        """Check for Z-score mean reversion signal."""
        signal = 'HOLD'
        confidence = 50
        reasoning = "No Z-signal"

        if abs(z_score) >= threshold and persistence >= min_persistence:
            signal = 'SELL' if z_score > 0 else 'BUY'
            confidence = min(95, abs(z_score) * 50)
            reasoning = f"Z={z_score:.2f}>={threshold}, persist={persistence}>={min_persistence}"
            logger.info(f"   🔥 Z-SIGNAL {pair}: {signal} (conf={confidence:.1f}%, z={z_score:.2f})")

        elif abs(z_score) >= threshold and persistence < min_persistence:
            reasoning = f"Z={z_score:.2f}>=threshold but persist={persistence}<{min_persistence}"
            logger.debug(f"   ⏳ {pair}: Building (z={z_score:.2f}, persist={persistence}/{min_persistence})")

        return {'signal': signal, 'confidence': confidence, 'reasoning': reasoning}

    # ============================================================
    # LEVEL 2: RL AGENT
    # ============================================================

    def _check_rl(self, pair, market_data, z_score, threshold):
        """Check RL agent override."""
        if not self.rl_agent:
            return {'signal': 'HOLD', 'confidence': 0, 'needs_hybrid': False}

        try:
            obs = self._build_rl_obs(pair, market_data)
            rl_action = self.rl_agent.predict(obs, deterministic=True)

            pair_idx = int(np.clip(rl_action[0], 0, len(self.brokers)-1))
            trade_type = int(np.clip(rl_action[1], 0, 2))

            pairs_list = list(self.brokers.keys())
            if pair_idx >= len(pairs_list) or pairs_list[pair_idx] != pair:
                return {'signal': 'HOLD', 'confidence': 0, 'needs_hybrid': False}

            if trade_type == 0:
                return {'signal': 'HOLD', 'confidence': 0, 'needs_hybrid': False}

            signal = 'BUY' if trade_type == 1 else 'SELL'
            z_peaked = abs(z_score) >= threshold
            needs_hybrid = not z_peaked

            reasoning = f"RL {signal}: Z {'peaked' if z_peaked else 'not peaked'} (z={z_score:.2f})"
            logger.info(f"   🤖 RL {pair}: {signal} (z={z_score:.2f}, needs_hybrid={needs_hybrid})")

            return {'signal': signal, 'confidence': 80, 'needs_hybrid': needs_hybrid, 'reasoning': reasoning}

        except Exception as e:
            logger.debug(f"RL check error: {e}")
            return {'signal': 'HOLD', 'confidence': 0, 'needs_hybrid': False}

    def _hybrid_confirms(self, pair, signal, market_data):
        """Check if Hybrid Coordinator confirms RL signal."""
        if not self.hybrid_coordinator:
            return True
        try:
            hybrid_data = {'rl_signal': {'vote': signal, 'confidence': 80, 'pair': pair}}
            decision = self.hybrid_coordinator.decide(hybrid_data)
            if decision.get('action') == signal:
                logger.info(f"   ✅ Hybrid CONFIRMS RL {signal} for {pair}")
                return True
            else:
                logger.info(f"   ❌ Hybrid REJECTS RL {signal} for {pair}")
                return False
        except Exception as e:
            logger.warning(f"Hybrid error: {e}")
            return False

    # ============================================================
    # MONTE CARLO GATE
    # ============================================================

    def _monte_carlo_gate(self, pair, signal, price, market_data, broker_result):
        """Monte Carlo gate - blocks bad entries only."""
        if not self.monte_carlo or price <= 0:
            return {
                'allowed': True, 'mc_confidence': 50, 'position_size': 0.03,
                'sl': price*0.99, 'tp': price*1.01, 'sr_risk': 0,
                'reasoning': 'No MC - default allow'
            }

        try:
            mc = self.monte_carlo.simulate_entry(
                current_price=price, direction=signal,
                price_history=market_data.get(f'{pair}_price_history', []),
                atr=market_data.get(f'{pair}_atr', 0)
            )

            mc_conf = mc.get('entry_confidence', 0)
            support = mc.get('support', market_data.get(f'{pair}_support', 0))
            resistance = mc.get('resistance', market_data.get(f'{pair}_resistance', 0))

            sr_risk = 0
            atr = market_data.get(f'{pair}_atr', price * 0.001)

            if signal == 'BUY' and resistance > 0:
                dist = resistance - price
                if 0 < dist < 2*atr:
                    sr_risk = 1 - (dist / (2*atr))
            elif signal == 'SELL' and support > 0:
                dist = price - support
                if 0 < dist < 2*atr:
                    sr_risk = 1 - (dist / (2*atr))

            if sr_risk > self.mc_sr_block_threshold:
                return {
                    'allowed': False, 'mc_confidence': mc_conf,
                    'position_size': 0, 'sl': 0, 'tp': 0,
                    'sr_risk': sr_risk,
                    'reasoning': f"S/R risk {sr_risk:.1%}"
                }

            if mc_conf < self.mc_min_confidence:
                return {
                    'allowed': False, 'mc_confidence': mc_conf,
                    'position_size': 0, 'sl': 0, 'tp': 0,
                    'sr_risk': sr_risk,
                    'reasoning': f"MC confidence {mc_conf:.1f}% < {self.mc_min_confidence}%"
                }

            size = self._calc_size(mc_conf, broker_result.get('volatility', 0.01),
                                   market_data.get('account_balance', 10000))
            sl_tp = self._calc_sl_tp(price, signal, broker_result.get('volatility', 0.01))

            return {
                'allowed': True, 'mc_confidence': mc_conf,
                'position_size': size, 'sl': sl_tp['sl'], 'tp': sl_tp['tp'],
                'sr_risk': sr_risk,
                'reasoning': f"MC={mc_conf:.1f}%, S/R risk={sr_risk:.1%}"
            }

        except Exception as e:
            logger.error(f"MC gate error: {e}")
            return {
                'allowed': True, 'mc_confidence': 50, 'position_size': 0.01,
                'sl': price*0.99, 'tp': price*1.01, 'sr_risk': 0,
                'reasoning': f'MC error: {e}'
            }

    def _calc_size(self, confidence, volatility, balance):
        """Volatility-adjusted position sizing."""
        base = 0.03
        conf_f = 0.5 + (confidence/100)*0.5
        vol_f = max(0.3, min(1.0, 1.0/(1.0+volatility*100)))
        acc_f = min(2.0, balance/10000)
        size = base * conf_f * vol_f * acc_f
        return max(0.01, min(0.10, round(size, 2)))

    def _calc_sl_tp(self, price, signal, volatility):
        """ATR-based SL/TP."""
        atr = price * volatility * 2
        if signal == 'BUY':
            return {'sl': price-atr*1.5, 'tp': price+atr*3.0}
        return {'sl': price+atr*1.5, 'tp': price-atr*3.0}

    def _build_rl_obs(self, pair, market_data):
        """Build RL observation vector."""
        obs = np.zeros(50, dtype=np.float32)
        obs[0] = market_data.get(pair, 0)
        broker = self.brokers.get(pair)
        if broker:
            obs[1] = getattr(broker, 'z_score', 0)
        return obs

    def get_broker_status(self):
        status = {}
        for pair, broker in self.brokers.items():
            status[pair] = {
                'z_score': getattr(broker, 'z_score', 0),
                'persistence': getattr(broker, 'persistence', 0),
                'signal': getattr(broker, 'signal', 'HOLD')
            }
        return status

    def get_broker(self, pair: str):
        return self.brokers.get(pair)