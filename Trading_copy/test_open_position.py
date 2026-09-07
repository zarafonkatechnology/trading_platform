# test_balance_change.py
"""
Test balance changes after trades
Simulates client with $20,000 balance
"""

import requests
import json
import time
from datetime import datetime
import sys

# API URL
API_URL = "http://localhost:8000/api/v1"

class BalanceTester:
    def __init__(self, initial_balance=20000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.equity = initial_balance
        self.trades = []
        self.total_pnl = 0.0
        
    def get_account_info(self):
        """Get account info from dashboard"""
        try:
            response = requests.get(f"{API_URL}/dashboard/data")
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data:
                    account = data['data']
                    self.current_balance = account.get('balance', self.current_balance)
                    self.equity = account.get('equity', self.equity)
                    return {
                        'balance': self.current_balance,
                        'equity': self.equity,
                        'profit': account.get('profit', 0)
                    }
        except Exception as e:
            print(f"   ⚠️ Could not get account info: {e}")
        return None
    
    def get_prices(self):
        """Get current prices"""
        try:
            response = requests.get(f"{API_URL}/controllers/all/prices")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    prices = data.get('data', {})
                    all_prices = {**prices.get('indices', {}), **prices.get('forex', {})}
                    return all_prices
        except Exception as e:
            print(f"   ⚠️ Could not get prices: {e}")
        return {}
    
    def execute_trade(self, symbol, order_type, volume, stop_loss=0, take_profit=0):
        """Execute a trade and track balance change"""
        print(f"\n   📊 Executing {order_type} on {symbol} ({volume} lots)")
        
        # Get price before trade
        prices = self.get_prices()
        price = prices.get(symbol, 0)
        if price <= 0:
            print(f"   ❌ No price for {symbol}")
            return None
        
        # Check if we have enough balance
        risk = volume * 100000  # Risk in dollars (simplified)
        if risk > self.current_balance * 0.1:  # Max 10% per trade
            print(f"   ⚠️ Risk ${risk:.2f} exceeds 10% of balance (${self.current_balance:.2f})")
            print(f"   ⏸️ Reducing volume to safe level")
            volume = (self.current_balance * 0.05) / 100000  # 5% risk
            volume = max(0.01, round(volume, 2))
            print(f"   📊 Adjusted volume to {volume} lots")
        
        # Execute trade via API
        try:
            response = requests.post(
                f"{API_URL}/trades/execute",
                params={
                    "symbol": symbol,
                    "order_type": order_type,
                    "volume": volume,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "comment": f"Balance test trade from client"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    trade_data = {
                        'symbol': symbol,
                        'type': order_type,
                        'volume': volume,
                        'entry_price': price,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.trades.append(trade_data)
                    
                    # Simulate P&L for demo (will be updated by actual MT4)
                    print(f"   ✅ Trade executed at ${price:.2f}")
                    return trade_data
                else:
                    print(f"   ❌ Trade failed: {data.get('error', 'Unknown error')}")
                    return None
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def get_positions(self):
        """Get current positions"""
        try:
            response = requests.get(f"{API_URL}/trades/positions")
            if response.status_code == 200:
                data = response.json()
                return data.get('positions', [])
        except Exception as e:
            print(f"   ⚠️ Could not get positions: {e}")
        return []
    
    def close_position(self, symbol):
        """Close a position"""
        try:
            response = requests.post(f"{API_URL}/trades/close/{symbol}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"   ✅ Position {symbol} closed")
                    return data
                else:
                    print(f"   ❌ Could not close: {data.get('error', 'Unknown')}")
                    return None
        except Exception as e:
            print(f"   ❌ Error closing position: {e}")
            return None
    
    def simulate_price_change(self, symbol, change_percent):
        """Simulate price change for testing"""
        prices = self.get_prices()
        price = prices.get(symbol, 0)
        if price > 0:
            new_price = price * (1 + change_percent / 100)
            print(f"   📊 Simulated price change: ${price:.2f} → ${new_price:.2f} ({change_percent:+.1f}%)")
            return new_price
        return 0
    
    def calculate_pnl(self, position, current_price):
        """Calculate P&L for a position"""
        entry = position.get('entry_price', 0)
        volume = position.get('volume', 0)
        order_type = position.get('type', 'BUY')
        
        if order_type == 'BUY':
            pnl = (current_price - entry) * volume * 100000
        else:
            pnl = (entry - current_price) * volume * 100000
        
        return round(pnl, 2)
    
    def print_status(self):
        """Print current status"""
        print("\n" + "=" * 60)
        print(f"📊 ACCOUNT STATUS")
        print("=" * 60)
        print(f"   Balance:  ${self.current_balance:>10.2f}")
        print(f"   Equity:   ${self.equity:>10.2f}")
        print(f"   P&L:      ${self.total_pnl:>10.2f}")
        print(f"   Trades:   {len(self.trades)}")
        
        positions = self.get_positions()
        if positions:
            print(f"\n   Open Positions:")
            for pos in positions:
                pnl = pos.get('pnl', 0)
                pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
                print(f"      - {pos.get('symbol')}: {pos.get('type')} {pos.get('volume')} lots @ {pos.get('entry_price', 0):.2f} (P&L: {pnl_str})")
        else:
            print(f"\n   No open positions")
        
        print("=" * 60)
    
    def run_full_test(self):
        """Run complete balance test"""
        print("=" * 60)
        print("💰 BALANCE CHANGE TEST")
        print(f"   Client Balance: ${self.initial_balance:,.2f}")
        print("=" * 60)
        
        # 1. Get initial account info
        print("\n1️⃣ Getting initial account info...")
        account = self.get_account_info()
        if account:
            print(f"   Balance: ${account.get('balance', 0):.2f}")
            print(f"   Equity: ${account.get('equity', 0):.2f}")
        
        # 2. Get available symbols
        print("\n2️⃣ Getting available symbols...")
        try:
            response = requests.get(f"{API_URL}/trades/symbols")
            if response.status_code == 200:
                data = response.json()
                symbols = data.get('symbols', [])[:6]
                print(f"   ✅ Available: {symbols}")
            else:
                print(f"   ❌ Error: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. Execute BUY trade on EURUSD
        print("\n3️⃣ Opening BUY position on EURUSD...")
        trade1 = self.execute_trade("EURUSD", "BUY", 0.02)
        if trade1:
            print(f"   ✅ Entry price: ${trade1['entry_price']:.5f}")
        
        # Check balance after trade
        time.sleep(1)
        account = self.get_account_info()
        if account:
            print(f"   📊 Balance after BUY: ${account.get('balance', 0):.2f}")
        
        # 4. Execute SELL trade on GOLD
        print("\n4️⃣ Opening SELL position on GOLD...")
        trade2 = self.execute_trade("GOLD", "SELL", 0.02)
        if trade2:
            print(f"   ✅ Entry price: ${trade2['entry_price']:.2f}")
        
        # Check balance after second trade
        time.sleep(1)
        account = self.get_account_info()
        if account:
            print(f"   📊 Balance after SELL: ${account.get('balance', 0):.2f}")
        
        # 5. Show all positions
        print("\n5️⃣ Current positions:")
        positions = self.get_positions()
        if positions:
            for pos in positions:
                print(f"   - {pos.get('symbol')}: {pos.get('type')} {pos.get('volume')} lots @ {pos.get('entry_price', 0):.2f}")
                if pos.get('pnl'):
                    print(f"     P&L: ${pos.get('pnl'):.2f}")
        else:
            print("   ℹ️ No positions found")
        
        # 6. Simulate price movement (for testing)
        print("\n6️⃣ Simulating price movement...")
        if positions:
            for pos in positions:
                symbol = pos.get('symbol')
                current_price = pos.get('entry_price', 0)
                # Simulate small movement
                move = 0.001 if symbol == 'EURUSD' else 5.0
                new_price = current_price + move
                pnl = self.calculate_pnl(pos, new_price)
                print(f"   {symbol}: ${current_price:.2f} → ${new_price:.2f} (P&L: ${pnl:.2f})")
                self.total_pnl += pnl
        
        # 7. Final status
        self.print_status()
        
        print("\n" + "=" * 60)
        print("✅ Test complete!")
        print("=" * 60)

def main():
    """Main test function"""
    tester = BalanceTester(initial_balance=20000.0)
    tester.run_full_test()
    
    print("\n💡 To see balance changes, run this test multiple times")
    print("   or manually check the dashboard at http://localhost:8000")

if __name__ == "__main__":
    main()