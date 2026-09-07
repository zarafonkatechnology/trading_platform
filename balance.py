# final_test_fixed.py
import os
import json
import time

MT4_PATH = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/50CA3DFB510CC5A8F28B48D1BF2A5702/MQL4/Files/"
COMMAND_FILE = os.path.join(MT4_PATH, "AI_Commands.txt")
RESPONSE_FILE = os.path.join(MT4_PATH, "AI_Responses.txt")

def send_command(cmd, timeout=15):
    """Send command and wait for response"""
    try:
        # Clean up old response file
        if os.path.exists(RESPONSE_FILE):
            try:
                os.remove(RESPONSE_FILE)
            except:
                pass
        
        # Write command
        with open(COMMAND_FILE, 'w') as f:
            json.dump(cmd, f)
        
        print(f"Command sent: {cmd}")
        
        # Wait for response
        start = time.time()
        while time.time() - start < timeout:
            if os.path.exists(RESPONSE_FILE):
                try:
                    with open(RESPONSE_FILE, 'r') as f:
                        response = json.load(f)
                    print(f"Response received at {time.time() - start:.1f} seconds")
                    return response
                except Exception as e:
                    print(f"Error reading response: {e}")
            time.sleep(0.5)
            print(f"Waiting... ({int(time.time() - start)}s)")
        
        print(f"Timeout after {timeout} seconds")
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

print("=" * 50)
print("Testing EA Communication")
print("=" * 50)

# Test PING
print("\n1. Testing PING...")
result = send_command({"command": "PING"}, timeout=10)
print(f"Result: {result}")

# Test ACCOUNT
print("\n2. Testing ACCOUNT...")
result = send_command({"command": "ACCOUNT"}, timeout=10)
if result:
    print(f"Balance: ${result.get('balance', 0):.2f}")
else:
    print("No response")

# Test NASDAQ
print("\n3. Testing NASDAQ100...")
result = send_command({"command": "PRICE", "symbol": "#NASDAQ100"}, timeout=15)
if result:
    print(f"Symbol: {result.get('symbol')}")
    print(f"Bid: {result.get('bid')}")
    print(f"Ask: {result.get('ask')}")
    print(f"✅ NASDAQ100 Price: ${(result.get('bid', 0) + result.get('ask', 0)) / 2:.2f}")
else:
    print("No response")

print("\n" + "=" * 50)