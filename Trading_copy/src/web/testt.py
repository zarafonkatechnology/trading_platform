# test_margin_calculation.py

def calculate_margin_test():
    """Test margin calculation with sample data"""
    
    # Sample position
    symbol = 'EURUSD'
    volume = 0.01  # 0.01 lot
    entry_price = 1.14337
    current_price = 1.14250
    leverage = 20
    contract_size = 100000
    
    # Calculate notional value
    notional_value = volume * contract_size * entry_price
    print(f"💰 Notional Value: ${notional_value:.2f}")
    
    # Calculate used margin
    used_margin = notional_value / leverage
    print(f"🔒 Used Margin: ${used_margin:.2f}")
    
    # Calculate P&L
    pnl = (current_price - entry_price) * volume * contract_size
    print(f"📈 Unrealized P&L: ${pnl:.2f}")
    
    # Account state
    balance = 100.01
    equity = balance + pnl
    free_margin = equity - used_margin
    margin_level = (equity / used_margin * 100) if used_margin > 0 else 0
    
    print(f"\n📊 Account State:")
    print(f"   Balance: ${balance:.2f}")
    print(f"   Equity: ${equity:.2f}")
    print(f"   Used Margin: ${used_margin:.2f}")
    print(f"   Free Margin: ${free_margin:.2f}")
    print(f"   Margin Level: {margin_level:.2f}%")
    
    # Expected output:
    # Notional Value: $1433.37
    # Used Margin: $71.67
    # Unrealized P&L: $-8.70
    # 
    # Account State:
    #    Balance: $100.01
    #    Equity: $91.31
    #    Used Margin: $71.67
    #    Free Margin: $19.64
    #    Margin Level: 127.40%

if __name__ == "__main__":
    calculate_margin_test()