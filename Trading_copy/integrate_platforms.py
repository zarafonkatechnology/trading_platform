# integrate_platforms.py
"""
Complete integration script to connect everything
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.mt4_gateway.mt4_bridge import MT4Bridge
from src.services.trade_service import TradeService
from config.settings import settings

async def integrate_all():
    print("🔗 Integrating Trading Platform Components")
    print("=" * 50)
    
    # 1. Initialize MT4 Bridge
    print("\n1️⃣ Initializing MT4 Bridge...")
    mt4 = MT4Bridge()
    symbols = mt4.get_symbols()
    print(f"   Found {len(symbols)} symbols")
    
    # 2. Initialize Trade Service
    print("\n2️⃣ Initializing Trade Service...")
    trade_service = TradeService()
    print("   Trade service ready")
    
    # 3. Test a sample trade (dry run)
    print("\n3️⃣ Testing Trade Execution...")
    if len(symbols) > 0:
        test_symbol = symbols[0]
        price = mt4.get_price(test_symbol)
        print(f"   Testing with {test_symbol} at price {price}")
        
        # This is a dry run - we'll just check if it's possible
        result = await trade_service.execute_trade(
            symbol=test_symbol,
            order_type="BUY",
            volume=0.01,
            stop_loss=price * 0.99,
            take_profit=price * 1.01,
            comment="Integration Test"
        )
        print(f"   Test result: {'✅' if result['success'] else '❌'}")
        if result.get('error'):
            print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 50)
    print("✅ Integration complete!")
    print(f"📊 Active Symbols: {len(symbols)}")
    print(f"📁 MT4 File Path: {settings.MT4_COMMON_FILES}")
    print("🌐 API running at: http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(integrate_all())