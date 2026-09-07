"""
Macro Consensus Conformity Agent
Hierarchical decision making for all macro factors
"""

from datetime import datetime
from enum import Enum

class MacroSignal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    CAUTIOUS_BUY = "CAUTIOUS_BUY"
    HOLD = "HOLD"
    CAUTIOUS_SELL = "CAUTIOUS_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    BLOCKED = "BLOCKED"

class ConformityAgent:
    """
    Macro-Intelligence Conformity Agent
    Processes agents in hierarchical order:
    
    Stage A: Context Agents (Seasonality + Intermarket) → Monthly Bias
    Stage B: Event Agent (Economic Calendar) → Red Light/Green Light
    Stage C: Truth Agents (Market Profile + Sentiment) → Fair Value + Mood
    """
    
    def __init__(self):
        self.rule_triggered = None
        self.position_multiplier = 1.0
        self.is_blocked = False
        
    def evaluate(self, seasonality, intermarket, economic, market_profile, sentiment, technical_vote=None):
        """
        Hierarchical evaluation of all macro factors
        
        Hierarchy:
        1. ECONOMIC CALENDAR = SUPREME AUTHORITY (Can block everything)
        2. SEASONALITY + INTERMARKET = Context (Reduces position size if conflicting)
        3. MARKET PROFILE + SENTIMENT = Truth (Provides contrarian signals)
        4. TECHNICAL = Lowest priority (Only if macro allows)
        """
        
        # ============ STAGE B: SUPREME AUTHORITY - Economic Calendar ============
        if economic.get('is_blocked', False):
            self.rule_triggered = "ECONOMIC CALENDAR BLOCK"
            self.is_blocked = True
            return {
                'signal': MacroSignal.BLOCKED,
                'action': 'HOLD',
                'confidence': 5,
                'reasoning': f"🔴 SUPREME AUTHORITY: {economic.get('block_reason', 'High impact event pending')}",
                'position_multiplier': 0,
                'risk_level': 'CRITICAL',
                'stage': 'B - Economic Calendar'
            }
        
        # ============ STAGE A: Context Agents ============
        context_score = 50
        context_reasons = []
        
        # Seasonality effect
        seasonality_vote = seasonality.get('vote', 'HOLD')
        seasonality_mult = seasonality.get('position_multiplier', 1.0)
        if seasonality_vote == 'BUY':
            context_score += 10
            context_reasons.append("📅 Seasonality bullish")
        elif seasonality_vote == 'SELL':
            context_score -= 10
            context_reasons.append("📅 Seasonality bearish")
        
        # Intermarket effect
        intermarket_vote = intermarket.get('vote', 'HOLD')
        risk_score = intermarket.get('risk_score', 50)
        if intermarket_vote == 'BUY':
            context_score += risk_score / 10
            context_reasons.append(f"🌍 Risk-on regime ({risk_score:.0f}%)")
        elif intermarket_vote == 'SELL':
            context_score -= (100 - risk_score) / 10
            context_reasons.append(f"🌍 Risk-off regime ({risk_score:.0f}%)")
        
        # Apply context multiplier
        if context_score < 40:
            self.position_multiplier = 0.5
            context_reasons.append("⚠️ Reducing position size by 50% due to conflicting context")
        else:
            self.position_multiplier = 1.0
        
        # ============ STAGE C: Truth Agents ============
        truth_score = 50
        truth_reasons = []
        
        # Market Profile (Fair Value)
        profile_vote = market_profile.get('vote', 'HOLD')
        is_fair_value = market_profile.get('is_fair_value', True)
        
        if profile_vote == 'BUY' and not is_fair_value:
            truth_score += 20
            truth_reasons.append("💰 Price at discount zone")
        elif profile_vote == 'SELL' and not is_fair_value:
            truth_score -= 20
            truth_reasons.append("⚠️ Price at premium zone")
        
        # Sentiment (Contrarian signals)
        sentiment_vote = sentiment.get('vote', 'HOLD')
        is_contrarian = sentiment.get('is_contrarian_signal', False)
        
        if is_contrarian:
            if sentiment_vote == 'BUY':
                truth_score += 25
                truth_reasons.append("🎯 CONTRARIAN: Extreme fear = BUY signal")
            elif sentiment_vote == 'SELL':
                truth_score -= 25
                truth_reasons.append("🎯 CONTRARIAN: Extreme greed = SELL signal")
        
        # ============ FINAL DECISION MATRIX ============
        
        # Apply economic calendar adjustment
        economic_mult = economic.get('position_multiplier', 1.0)
        final_multiplier = self.position_multiplier * economic_mult
        
        # Calculate final confidence
        base_confidence = (context_score + truth_score) / 2
        final_confidence = base_confidence * final_multiplier
        
        # Determine final signal
        if final_multiplier == 0:
            final_signal = MacroSignal.BLOCKED
            final_action = "HOLD"
            final_reasoning = "🔴 TRADING BLOCKED: Economic calendar event pending"
        
        elif final_confidence > 75:
            final_signal = MacroSignal.STRONG_BUY if context_score > truth_score else MacroSignal.STRONG_SELL
            final_action = "BUY" if context_score > 50 else "SELL"
            final_reasoning = f"✅ STRONG MACRO ALIGNMENT: {', '.join(context_reasons + truth_reasons)}"
        
        elif final_confidence > 60:
            final_signal = MacroSignal.BUY if context_score > 50 else MacroSignal.SELL
            final_action = "BUY" if context_score > 50 else "SELL"
            final_reasoning = f"✓ Macro bias: {', '.join(context_reasons + truth_reasons)}"
        
        elif final_confidence > 45:
            final_signal = MacroSignal.CAUTIOUS_BUY if context_score > 50 else MacroSignal.CAUTIOUS_SELL
            final_action = "CAUTIOUS_BUY" if context_score > 50 else "CAUTIOUS_SELL"
            final_reasoning = f"⚠️ Mixed macro signals. Position size reduced. {', '.join(context_reasons)}"
        
        else:
            final_signal = MacroSignal.HOLD
            final_action = "HOLD"
            final_reasoning = f"❌ MACRO CONFLICT: {', '.join(context_reasons)} vs {', '.join(truth_reasons)}"
        
        return {
            'signal': final_signal,
            'action': final_action,
            'confidence': round(final_confidence, 1),
            'reasoning': final_reasoning,
            'position_multiplier': final_multiplier,
            'context_score': round(context_score, 1),
            'truth_score': round(truth_score, 1),
            'context_reasons': context_reasons,
            'truth_reasons': truth_reasons,
            'stage': 'Macro Consensus Complete',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_hierarchy_diagram(self):
        """Return the macro hierarchy for documentation"""
        return """
        ┌─────────────────────────────────────────────────────────────────┐
        │              MACRO-INTELLIGENCE HIERARCHY                       │
        ├─────────────────────────────────────────────────────────────────┤
        │                                                                  │
        │  STAGE B: SUPREME AUTHORITY (Red Light/Green Light)            │
        │  ┌─────────────────────────────────────────────────────────┐    │
        │  │  ECONOMIC CALENDAR → Can BLOCK all trading              │    │
        │  │  • NFP, FOMC, CPI within 60 mins = NO TRADE             │    │
        │  └─────────────────────────────────────────────────────────┘    │
        │                              │                                   │
        │                              ▼                                   │
        │  STAGE A: Context Agents (The "Wind")                          │
        │  ┌─────────────────────────────────────────────────────────┐    │
        │  │  SEASONALITY + INTERMARKET → Monthly Bias               │    │
        │  │  • "Sell in May" effect                                 │    │
        │  │  • Risk-on/Risk-off regime                              │    │
        │  │  • Position size -50% if conflicting                    │    │
        │  └─────────────────────────────────────────────────────────┘    │
        │                              │                                   │
        │                              ▼                                   │
        │  STAGE C: Truth Agents (The "Mood" & "Auction")                │
        │  ┌─────────────────────────────────────────────────────────┐    │
        │  │  MARKET PROFILE + SENTIMENT → Fair Value + Contrarian   │    │
        │  │  • Buy undervalued, sell overvalued                     │    │
        │  │  • Extreme sentiment = Contrarian signal                │    │
        │  └─────────────────────────────────────────────────────────┘    │
        │                              │                                   │
        │                              ▼                                   │
        │  STAGE D: Technical Agents (Lowest Priority)                   │
        │  ┌─────────────────────────────────────────────────────────┐    │
        │  │  ICHIMOKU + VOLUME + OTHERS → Entry Timing              │    │
        │  │  • Only if macro allows                                 │    │
        │  │  • Position size × macro multiplier                     │    │
        │  └─────────────────────────────────────────────────────────┘    │
        │                                                                  │
        └─────────────────────────────────────────────────────────────────┘
        """
