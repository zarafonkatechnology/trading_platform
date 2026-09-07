# fix_ea_order.py
"""
FIX EA ORDER ISSUES - COMPLETE SOLUTION
Orders will appear in MT4 Terminal
"""

import os
import json
import time
import sys
from datetime import datetime
from mt4_price_provider import get_mt4_prices

# ============ CONFIGURATION ============
MT4_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
COMMAND_FILE = os.path.join(MT4_PATH, "AI_Commands.txt")
RESPONSE_FILE = os.path.join(MT4_PATH, "AI_Responses.txt")
ORDER_FILE = os.path.join(MT4_PATH, "AI_Orders.txt")  # Alternative

# ============ HELPER FUNCTIONS ============

def clear_files():
    """Clear command and response files"""
    try:
        if os.path.exists(COMMAND_FILE):
            os.remove(COMMAND_FILE)
            print("   ✅ Cleared AI_Commands.txt")
        if os.path.exists(RESPONSE_FILE):
            os.remove(RESPONSE_FILE)
            print("   ✅ Cleared AI_Responses.txt")
    except Exception as e:
        print(f"   ⚠️ Could not clear files: {e}")

def check_mt4_files():
    """Check if MT4 files exist"""
    print("\n📁 Checking MT4 Files:")
    
    files = [
        COMMAND_FILE,
        RESPONSE_FILE,
        ORDER_FILE,
        "AI_Trading_EA.ex4",
        "AI_Trading_EA.mq4"
    ]
    
    for f in files:
        exists = os.path.exists(f)
        size = os.path.getsize(f) if exists else 0
        status = "✅" if exists else "❌"
        print(f"   {status} {os.path.basename(f)}: {size} bytes" if exists else f"   {status} {os.path.basename(f)}: NOT FOUND")

def send_command_to_ea(command):
    """Send command to EA via file"""
    try:
        # Clear old command
        if os.path.exists(COMMAND_FILE):
            os.remove(COMMAND_FILE)
        
        # Write new command
        with open(COMMAND_FILE, 'w') as f:
            if isinstance(command, dict):
                json.dump(command, f)
            else:
                f.write(command)
        
        print(f"   📤 Sent: {command}")
        return True
    except Exception as e:
        print(f"   ❌ Error sending command: {e}")
        return False

def wait_for_response(timeout=10):
    """Wait for EA response"""
    print("   ⏳ Waiting for EA response...")
    
    for i in range(timeout):
        if os.path.exists(RESPONSE_FILE):
            try:
                with open(RESPONSE_FILE, 'r') as f:
                    content = f.read()
                    if content:
                        print(f"   📥 Response: {content[:200]}...")
                        return content
            except:
                pass
        time.sleep(1)
        print(f"   ⏳ {i+1}s...", end="\r")
    
    print("\n   ⏰ Timeout - No response from EA")
    return None

# ============ TEST FUNCTIONS ============

def test_ping():
    """Test if EA responds to PING"""
    print("\n" + "=" * 60)
    print("🔍 TESTING EA CONNECTION")
    print("=" * 60)
    
    clear_files()
    
    # Send PING
    if send_command_to_ea("PING"):
        response = wait_for_response(5)
        if response:
            print("   ✅ EA is RESPONDING!")
            return True
        else:
            print("   ❌ EA is NOT RESPONDING!")
            print("\n   Please check:")
            print("   1. MT4 is running")
            print("   2. EA is attached to a chart")
            print("   3. AutoTrading is ON (green button)")
            return False
    return False

def test_order_buy():
    """Test BUY order"""
    print("\n" + "=" * 60)
    print("📊 TESTING BUY ORDER")
    print("=" * 60)
    
    # Get current price
    mt4 = get_mt4_prices()
    price_data = mt4._send({"command": "PRICE", "symbol": "EURUSD"})
    
    if not price_data or not price_data.get('bid'):
        print("❌ Cannot get price!")
        return False
    
    price = price_data['bid']
    symbol = 'EURUSD'
    volume = 0.01
    sl = price * 0.99
    tp = price * 1.02
    
    print(f"\n📊 Order Details:")
    print(f"   Symbol: {symbol}")
    print(f"   Action: BUY")
    print(f"   Volume: {volume} lots")
    print(f"   Price: {price:.5f}")
    print(f"   Stop Loss: {sl:.5f}")
    print(f"   Take Profit: {tp:.5f}")
    
    response = input("\n🚀 Execute BUY order? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return False
    
    # Build order command - Format that EA expects
    order_cmd = {
        "command": "ORDER",
        "symbol": symbol,
        "type": "BUY",
        "volume": volume,
        "sl": sl,
        "tp": tp
    }
    
    print("\n📝 Sending order to EA...")
    clear_files()
    
    if send_command_to_ea(order_cmd):
        response = wait_for_response(10)
        
        if response:
            try:
                result = json.loads(response)
                if result.get('success'):
                    print(f"\n✅ ORDER EXECUTED!")
                    print(f"   Ticket: {result.get('ticket')}")
                    print(f"   Price: {result.get('price'):.5f}")
                    print("\n📌 Check MT4 Terminal → Trade tab")
                    return True
                else:
                    print(f"\n❌ Order failed: {result.get('error')}")
                    return False
            except:
                print(f"\n📥 Response: {response}")
                return True
        else:
            print("\n❌ No response from EA!")
            return False
    return False

def test_order_sell():
    """Test SELL order"""
    print("\n" + "=" * 60)
    print("📊 TESTING SELL ORDER")
    print("=" * 60)
    
    # Get current price
    mt4 = get_mt4_prices()
    price_data = mt4._send({"command": "PRICE", "symbol": "EURUSD"})
    
    if not price_data or not price_data.get('bid'):
        print("❌ Cannot get price!")
        return False
    
    price = price_data['bid']
    symbol = 'EURUSD'
    volume = 0.01
    sl = price * 1.01
    tp = price * 0.98
    
    print(f"\n📊 Order Details:")
    print(f"   Symbol: {symbol}")
    print(f"   Action: SELL")
    print(f"   Volume: {volume} lots")
    print(f"   Price: {price:.5f}")
    print(f"   Stop Loss: {sl:.5f}")
    print(f"   Take Profit: {tp:.5f}")
    
    response = input("\n🚀 Execute SELL order? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled")
        return False
    
    # Build order command
    order_cmd = {
        "command": "ORDER",
        "symbol": symbol,
        "type": "SELL",
        "volume": volume,
        "sl": sl,
        "tp": tp
    }
    
    print("\n📝 Sending order to EA...")
    clear_files()
    
    if send_command_to_ea(order_cmd):
        response = wait_for_response(10)
        
        if response:
            try:
                result = json.loads(response)
                if result.get('success'):
                    print(f"\n✅ ORDER EXECUTED!")
                    print(f"   Ticket: {result.get('ticket')}")
                    print(f"   Price: {result.get('price'):.5f}")
                    print("\n📌 Check MT4 Terminal → Trade tab")
                    return True
                else:
                    print(f"\n❌ Order failed: {result.get('error')}")
                    return False
            except:
                print(f"\n📥 Response: {response}")
                return True
        else:
            print("\n❌ No response from EA!")
            return False
    return False

def check_positions():
    """Check open positions"""
    print("\n" + "=" * 60)
    print("📊 CHECKING OPEN POSITIONS")
    print("=" * 60)
    
    try:
        mt4 = get_mt4_prices()
        result = mt4._send({"command": "POSITIONS"})
        
        if result:
            positions = result.get('positions', [])
            if positions:
                print(f"\n✅ Found {len(positions)} open positions:")
                for pos in positions:
                    print(f"   {pos.get('symbol')}: {pos.get('type')} {pos.get('volume')} lots @ {pos.get('price'):.5f}")
                    print(f"      SL: {pos.get('sl', 'N/A')} | TP: {pos.get('tp', 'N/A')}")
                    print(f"      Profit: ${pos.get('profit', 0):.2f}")
            else:
                print("\n📭 No open positions")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ============ MAIN MENU ============

def main():
    print("=" * 70)
    print("🔧 FIX EA ORDER ISSUES - COMPLETE SOLUTION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Check MT4 files
    check_mt4_files()
    
    # Test EA connection first
    if not test_ping():
        print("\n" + "=" * 70)
        print("⚠️  EA NOT RESPONDING - TROUBLESHOOTING")
        print("=" * 70)
        print("\n📋 Please check the following:")
        print("   1️⃣ Is MT4 running? Check taskbar")
        print("   2️⃣ Is EA attached to a chart? Look for 'AI_Trading_EA'")
        print("   3️⃣ Is AutoTrading ON? The button should be GREEN")
        print("   4️⃣ Check Experts tab for errors: View → Experts")
        print("   5️⃣ Right-click the chart → Expert Advisors → Properties")
        print("      → Enable 'Allow Live Trading'")
        print("   6️⃣ Check MT4 Experts tab for error messages")
        print("\n   After fixing, run this script again!")
        return
    
    while True:
        print("\n" + "=" * 70)
        print("📋 MAIN MENU")
        print("=" * 70)
        print("1️⃣  Test PING (check EA connection)")
        print("2️⃣  BUY EURUSD 0.01 lot")
        print("3️⃣  SELL EURUSD 0.01 lot")
        print("4️⃣  Check Open Positions")
        print("5️⃣  Check MT4 Files")
        print("6️⃣  EXIT")
        
        choice = input("\n📌 Select option (1-6): ")
        
        if choice == '1':
            test_ping()
        elif choice == '2':
            test_order_buy()
        elif choice == '3':
            test_order_sell()
        elif choice == '4':
            check_positions()
        elif choice == '5':
            check_mt4_files()
        elif choice == '6':
            print("\n👋 Exiting...")
            break
        else:
            print("❌ Invalid choice. Try again.")
        
        time.sleep(1)

if __name__ == "__main__":
    main()