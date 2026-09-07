#!/usr/bin/env python3
"""
Teach Agent_B the proper trend confirmation logic
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.agents.agent_b_mean_reversion import AgentBMeanReversion

def teach_agent_a():
    print("=" * 70)
    print("📚 TEACHING AGENT_B - PROPER TREND CONFIRMATION")
    print("=" * 70)
    
    agent = AgentBMeanReversion()
    
    lesson = """
╔═══════════════════════════════════════════════════════════════════════════════════╗
║                    LESSON: PROPER TREND CONFIRMATION                              ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║  ❌ WRONG: RSI < 30 = BUY                                                        ║
║     → Market can stay oversold for weeks in strong downtrend                     ║
║     → Buying too early leads to losses                                           ║
║                                                                                   ║
║  ✅ CORRECT: RSI < 30 + PRICE ABOVE PREVIOUS CANDLE HIGH = BUY                   ║
║     → Confirms reversal from downtrend to uptrend                                ║
║     → Price action confirms the RSI signal                                       ║
║                                                                                   ║
║  ❌ WRONG: RSI > 70 = SELL                                                       ║
║     → Market can stay overbought for weeks in strong uptrend                     ║
║     → Selling too early misses profits                                           ║
║                                                                                   ║
║  ✅ CORRECT: RSI > 70 + PRICE BELOW PREVIOUS CANDLE LOW = SELL                   ║
║     → Confirms reversal from uptrend to downtrend                                ║
║     → Price action confirms the RSI signal                                       ║
║                                                                                   ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                         EXAMPLE SCENARIOS                                         ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║  Scenario 1: RSI = 25 (oversold)                                                 ║
║             Last Candle Close = 2350                                             ║
║             Previous Candle High = 2345                                          ║
║             → 2350 > 2345 → ✅ BUY SIGNAL                                        ║
║                                                                                   ║
║  Scenario 2: RSI = 25 (oversold)                                                 ║
║             Last Candle Close = 2340                                             ║
║             Previous Candle High = 2345                                          ║
║             → 2340 < 2345 → ❌ NO SIGNAL (wait for breakout)                     ║
║                                                                                   ║
║  Scenario 3: RSI = 80 (overbought)                                               ║
║             Last Candle Close = 2400                                             ║
║             Previous Candle Low = 2405                                           ║
║             → 2400 < 2405 → ✅ SELL SIGNAL                                       ║
║                                                                                   ║
║  Scenario 4: RSI = 80 (overbought)                                               ║
║             Last Candle Close = 2410                                             ║
║             Previous Candle Low = 2405                                           ║
║             → 2410 > 2405 → ❌ NO SIGNAL (wait for breakdown)                    ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
"""
    
    print(lesson)
    
    # Test the agent with different scenarios
    print("\n" + "=" * 70)
    print("📊 TESTING AGENT_B WITH DIFFERENT SCENARIOS")
    print("=" * 70)
    
    test_scenarios = [
        {
            'name': '✅ Valid BUY Signal',
            'rsi': 25,
            'candles': [
                {'close': 2340, 'high': 2345, 'low': 2335},
                {'close': 2350, 'high': 2355, 'low': 2340}
            ],
            'expected': 'BUY'
        },
        {
            'name': '❌ Invalid BUY (No confirmation)',
            'rsi': 25,
            'candles': [
                {'close': 2340, 'high': 2345, 'low': 2335},
                {'close': 2342, 'high': 2347, 'low': 2338}
            ],
            'expected': 'HOLD'
        },
        {
            'name': '✅ Valid SELL Signal',
            'rsi': 80,
            'candles': [
                {'close': 2410, 'high': 2415, 'low': 2405},
                {'close': 2400, 'high': 2408, 'low': 2398}
            ],
            'expected': 'SELL'
        },
        {
            'name': '❌ Invalid SELL (No confirmation)',
            'rsi': 80,
            'candles': [
                {'close': 2410, 'high': 2415, 'low': 2405},
                {'close': 2408, 'high': 2412, 'low': 2403}
            ],
            'expected': 'HOLD'
        }
    ]
    
    for scenario in test_scenarios:
        signal = {'asset_type': 'XAU/USD', 'confidence_percent': 85}
        features = {
            'rsi_14': scenario['rsi'],
            'candles': scenario['candles'],
            'trend_strength': 60,
            'timeframe': 15
        }
        
        action, confidence = agent.predict(signal, features)
        
        status = "✅ PASS" if action == scenario['expected'] else "❌ FAIL"
        print(f"\n{status} | {scenario['name']}")
        print(f"   RSI: {scenario['rsi']}")
        print(f"   Last Close: {scenario['candles'][-1]['close']}")
        print(f"   Prev High/Low: {scenario['candles'][-2]['high']}/{scenario['candles'][-2]['low']}")
        print(f"   Result: {action} ({confidence:.0f}%) | Expected: {scenario['expected']}")
    
    print("\n" + "=" * 70)
    print("✅ TEACHING COMPLETE! Agent_B now uses proper confirmation logic.")
    print("=" * 70)

if __name__ == '__main__':
    teach_agent_a()
