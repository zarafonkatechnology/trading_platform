#!/usr/bin/env python3
"""
Test OANDA Fetcher
"""

import sys
sys.path.insert(0, '/home/mohammed/trading_platform')

from backend.services.oanda_fetcher import get_oanda_fetcher
from colorama import Fore, Style, init

init(autoreset=True)

print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"{Fore.CYAN}OANDA DATA FETCHER TEST{Style.RESET_ALL}")
print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")

# Get fetcher
fetcher = get_oanda_fetcher()

print(f"\n{Fore.YELLOW}[1] Getting live prices...{Style.RESET_ALL}")
prices = fetcher.get_all_prices()

print(f"\n{Fore.GREEN}Current Market Prices:{Style.RESET_ALL}")
print("-" * 40)
for name, price in prices.items():
    if name in ['EURUSD', 'GBPUSD']:
        print(f"  {name}: {price:.4f}")
    else:
        print(f"  {name}: ${price:.2f}")

print(f"\n{Fore.YELLOW}[2] Getting candles for GOLD...{Style.RESET_ALL}")
candles = fetcher.get_candles('GOLD', count=10)
print(f"Got {len(candles)} candles")

if candles:
    latest = candles[-1]
    print(f"  Latest Gold: Open=${latest['open']:.2f}, Close=${latest['close']:.2f}")

print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
print(f"{Fore.GREEN}✅ OANDA Fetcher is working!{Style.RESET_ALL}")
print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
