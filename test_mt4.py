# Test one thing at a time, not all at once
print("Testing ACCOUNT...")
result = mt4._send({"command": "ACCOUNT"})
time.sleep(2)

print("Testing PRICE...")
result = mt4.get_price('EURUSD')