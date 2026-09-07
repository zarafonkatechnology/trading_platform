"""Test MT4 fallback mechanism when timeout occurs"""

import sys
from pathlib import Path

# Add workspace root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from mt4_price_provider import MT4PriceProvider


def test_fallback_account_data():
    """Verify fallback account data is returned when MT4 times out"""
    provider = MT4PriceProvider()
    fallback = provider._get_fallback_account_data()
    
    # Verify required fields exist
    assert fallback.get('balance') > 0, "Fallback should have positive balance"
    assert fallback.get('equity') > 0, "Fallback should have positive equity"
    assert fallback.get('success') == True, "Fallback should have success=True"
    assert fallback.get('source') == 'fallback', "Fallback should be marked as fallback"
    
    # Verify key pairs exist
    key_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'GOLD']
    for pair in key_pairs:
        assert pair in fallback, f"Fallback missing {pair}"
        assert fallback[pair] > 0, f"Fallback {pair} should have positive price"
    
    print("✅ Fallback account data structure verified")


def test_fallback_caching():
    """Verify fallback caches successful account data"""
    provider = MT4PriceProvider()
    
    # Simulate successful account data
    mock_data = {
        'balance': 50000,
        'equity': 48500,
        'EURUSD': 1.1420,
        'success': True
    }
    provider.last_account_data = mock_data
    
    # Get fallback - should return cached data
    cached = provider._get_fallback_account_data()
    assert cached == mock_data, "Fallback should return cached data first"
    assert cached['balance'] == 50000, "Cached balance should match"
    
    print("✅ Fallback caching mechanism verified")


def test_timeout_recovery():
    """Verify provider handles timeout gracefully"""
    provider = MT4PriceProvider()
    
    # Simulate timeout by requesting from non-existent path
    provider.command_file = "C:/NonExistent/Path/command.txt"
    
    result = provider._send({"command": "ACCOUNT"})
    
    # Should return fallback data for ACCOUNT requests, not error
    assert result.get('success') == True, "ACCOUNT timeout should return fallback with success=True"
    assert result.get('source') == 'fallback', "Timeout should be marked as fallback"
    assert result.get('balance') > 0, "Fallback balance should be positive"
    
    print("✅ Timeout recovery mechanism verified")


if __name__ == "__main__":
    test_fallback_account_data()
    test_fallback_caching()
    test_timeout_recovery()
    print("\n✅ All MT4 fallback tests passed")
