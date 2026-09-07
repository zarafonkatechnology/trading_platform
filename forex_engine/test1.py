# debug_balance.py
import asyncio
from src.database.supabase_client import get_trading_service
from src.api.routes.client_trades import execute_client_trade

async def debug_trade():
    print("🔍 DEBUG: Testing trade execution")
    
    # Get balance before trade
    trading_db = get_trading_service()
    result = trading_db.client.table('trading_balances')\
        .select('*')\
        .eq('user_id', 'test_user')\
        .execute()
    
    print(f"💰 Balance BEFORE: ${result.data[0]['balance']:.2f}")
    
    # Execute trade
    # ... call execute_client_trade ...
    
    # Get balance after trade
    result2 = trading_db.client.table('trading_balances')\
        .select('*')\
        .eq('user_id', 'test_user')\
        .execute()
    
    print(f"💰 Balance AFTER: ${result2.data[0]['balance']:.2f}")

asyncio.run(debug_trade())