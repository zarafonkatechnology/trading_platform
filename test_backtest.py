# test_backtest.py
"""
Test the backtesting system with real data
"""

from historical_data import historical_data
from backtest_engine import backtest_engine
from alpha_generator import alpha_generator

print("=" * 60)
print("BACKTESTING SYSTEM TEST")
print("=" * 60)

# 1. Test historical data retrieval
print("\n[1] Testing Historical Data Access...")
symbol = "#NASDAQ100"
hist_data = historical_data.get_price_history(symbol, days=7)
print(f"   Retrieved {len(hist_data)} candles for {symbol}")
print(f"   Date range: {hist_data.index[0]} to {hist_data.index[-1]}")
print(f"   Price range: ${hist_data['low'].min():.2f} - ${hist_data['high'].max():.2f}")

# 2. Generate and backtest an alpha
print("\n[2] Generating and Backtesting Alpha...")
alpha = alpha_generator.generate_new_alpha()
print(f"   Alpha: {alpha['name']}")

# Backtest
validated = alpha_generator.backtest_and_validate(alpha, symbol, days=30)
metrics = validated['backtest']['metrics']

print(f"\n[3] Backtest Results:")
print(f"   Total Trades: {metrics['total_trades']}")
print(f"   Win Rate: {metrics['win_rate']}%")
print(f"   Sharpe Ratio: {metrics['sharpe_ratio']}")
print(f"   Total Return: {metrics['total_return']}%")
print(f"   Max Drawdown: {metrics['max_drawdown']}%")
print(f"   Profit Factor: {metrics['profit_factor']}")

# 4. Validation result
print(f"\n[4] Validation: {'✅ PASSED' if validated['backtest']['passed'] else '❌ FAILED'}")

# 5. Find best alpha
print("\n[5] Finding Best Alpha...")
best = alpha_generator.get_top_performing_alpha()
if best:
    print(f"   Best Alpha: {best['name']}")
    print(f"   Win Rate: {best['backtest']['metrics']['win_rate']}%")
    print(f"   Sharpe: {best['backtest']['metrics']['sharpe_ratio']}")
else:
    print("   No validated alphas yet. Generate more!")

print("\n✅ Backtesting system ready!")