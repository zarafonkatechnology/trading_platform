# signal_formatter.py
from datetime import datetime

class SignalFormatter:
    """Format trading signals with AI pipeline data"""
    
    @staticmethod
    def format_enhanced_signal(symbol: str, signal_data: dict, 
                                agent_result: dict, flow_signal: dict,
                                mt4_connected: bool) -> str:
        """Format complete signal with AI consensus"""
        
        # Get agent consensus
        agent_decision = agent_result.get('decision', 'HOLD')
        agent_confidence = agent_result.get('confidence', 0)
        
        # Get flow signals
        cvd_signal = "🟢 Bullish" if flow_signal.get('cvd', 0) > 0 else "🔴 Bearish" if flow_signal.get('cvd', 0) < 0 else "⚪ Neutral"
        sweep = flow_signal.get('liquidity_sweep', {}).get('swept', 'None')
        
        message = f"""
📊 *{symbol} – {signal_data['action']}*

*🤖 AI DELIBERATIVE PIPELINE*
━━━━━━━━━━━━━━━━━━━━━
🧠 *Agent Consensus:* {agent_decision} ({agent_confidence:.0f}%)
   • 📈 Analyst: {agent_result.get('analyst_score', 0):.0f}
   • ⚖️ Challenger: {agent_result.get('challenger_score', 0):.0f}
   • ✅ Validator: {agent_result.get('validator_score', 0):.0f}

📊 *Order Flow Analysis*
   • CVD: {cvd_signal} ({abs(flow_signal.get('cvd', 0)):.0f})
   • Liquidity Sweep: {sweep if sweep != 'None' else 'None detected'}
   • Volume Profile: {flow_signal.get('volume_profile', 'Normal')}

{SignalFormatter._get_signal_details(signal_data)}

🎯 *AI Recommendation:* {signal_data['action']} at {signal_data['entry']}
🛑 *Stop Loss:* {signal_data['stop_loss']}
✅ *Take Profit:* {signal_data['take_profit_1']} / {signal_data['take_profit_2']}

📈 *Expected Move*
   • Range: {signal_data['expected_low']} → {signal_data['expected_high']}
   • Pips: {signal_data['expected_pips']} pips
   • Max Hold: {signal_data['max_hold']} minutes

📋 *Risk Metrics*
   • Success Prob: {signal_data.get('success_probability', 0)}%
   • Momentum Strength: {signal_data.get('momentum_strength', 0)}%
   • Volume Spike: {signal_data.get('volume_spike', 0)}x
   • Risk/Reward: 1:{signal_data.get('risk_reward', 0):.1f}

🔌 *System Status*
   • MT4 Bridge: {'✅ CONNECTED' if mt4_connected else '⚠️ SIMULATED'}
   • AI Version: Deliberative Pipeline v2.0
   • Strategy: {signal_data.get('strategy', 'Momentum')}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return message
    
    @staticmethod
    def _get_signal_details(signal_data: dict) -> str:
        """Get signal-specific details"""
        details = f"""
*📊 Signal Details*
━━━━━━━━━━━━━━━━━━━━━
• Level: {signal_data.get('level', signal_data.get('entry', 'N/A'))} ({signal_data.get('level_type', 'Key Level')})
• Timeframe: {signal_data.get('timeframe', '15m')}
• Certainty: {signal_data.get('certainty', 0)}% ({signal_data.get('certainty_label', 'Moderate')})
• Level Strength: {signal_data.get('level_strength', 'N/A')}
• Volume Ratio: {signal_data.get('volume_ratio', 1)}x avg
• Market Regime: {signal_data.get('market_regime', 'TRENDING')}
• Trend Strength: {signal_data.get('trend_strength', 0)}%
"""
        return details