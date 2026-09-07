"""
Asset Configuration for All Trading Strategies
Central place for asset-specific parameters
"""

ASSET_PARAMETERS = {
    # Forex majors
    'EURUSD': {'pip_size': 0.0001, 'normal_range_pips': 80, 'volatility_factor': 1.0, 'decimals': 4},
    'GBPUSD': {'pip_size': 0.0001, 'normal_range_pips': 80, 'volatility_factor': 1.0, 'decimals': 4},
    'USDJPY': {'pip_size': 0.01, 'normal_range_pips': 80, 'volatility_factor': 0.8, 'decimals': 2},
    'USDCHF': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
    'AUDUSD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
    'USDCAD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
    'NZDUSD': {'pip_size': 0.0001, 'normal_range_pips': 70, 'volatility_factor': 0.9, 'decimals': 4},
    
    # Metals
    'XAU/USD': {'pip_size': 0.01, 'normal_range_pips': 2000, 'volatility_factor': 1.2, 'decimals': 2},
    'XAG/USD': {'pip_size': 0.001, 'normal_range_pips': 50, 'volatility_factor': 1.1, 'decimals': 3},
    
    # Indices
    'NAS100/USD': {'pip_size': 0.1, 'normal_range_pips': 200, 'volatility_factor': 1.3, 'decimals': 1},
    'S&P500/USD': {'pip_size': 0.1, 'normal_range_pips': 50, 'volatility_factor': 1.0, 'decimals': 1},
    'DJ30/USD': {'pip_size': 0.1, 'normal_range_pips': 150, 'volatility_factor': 1.1, 'decimals': 1},
    'GER30/EUR': {'pip_size': 0.1, 'normal_range_pips': 150, 'volatility_factor': 1.0, 'decimals': 1},
    
    # Commodities
    'BCO/USD': {'pip_size': 0.01, 'normal_range_pips': 200, 'volatility_factor': 1.2, 'decimals': 2},
    'WTICO/USD': {'pip_size': 0.01, 'normal_range_pips': 200, 'volatility_factor': 1.2, 'decimals': 2},
    
    # Crypto (if you add later)
    'BTC/USD': {'pip_size': 1.0, 'normal_range_pips': 5000, 'volatility_factor': 2.0, 'decimals': 0},
}

# Aliases for common naming variations
ASSET_ALIASES = {
    'GOLD': 'XAU/USD',
    'GOLD': 'XAU/USD',
    'SILVER': 'XAG/USD',
    'SILVER': 'XAG/USD',
    'NAS100': 'NAS100/USD',
    'S&P500': 'S&P500/USD',
    'DJ30': 'DJ30/USD',
    'UK100': 'UK100/GBP',
    'BRENT_OIL': 'BCO/USD',
    'WTICUSD': 'WTICO/USD',
}


def get_asset_params(asset: str) -> dict:
    """Get parameters for an asset, handling aliases."""
    # Normalize asset name
    if asset in ASSET_ALIASES:
        asset = ASSET_ALIASES[asset]
    
    return ASSET_PARAMETERS.get(asset, ASSET_PARAMETERS['EURUSD'])


def calculate_expected_range(asset: str, current_price: float, volume_ratio: float) -> dict:
    """Calculate realistic expected price range for an asset."""
    params = get_asset_params(asset)
    pip_size = params['pip_size']
    normal_range_pips = params['normal_range_pips']
    decimals = params['decimals']
    
    # Expected move based on volume spike
    if volume_ratio > 2.5:
        expected_pips = normal_range_pips * 0.6
    elif volume_ratio > 2.0:
        expected_pips = normal_range_pips * 0.5
    elif volume_ratio > 1.5:
        expected_pips = normal_range_pips * 0.35
    else:
        expected_pips = normal_range_pips * 0.2
    
    # Cap at reasonable maximum
    max_pips = normal_range_pips * 0.8
    actual_pips = min(expected_pips, max_pips)
    
    # Convert to price
    move_price = actual_pips * pip_size
    
    return {
        'low': round(current_price - move_price, decimals),
        'high': round(current_price + move_price, decimals),
        'pips': round(actual_pips, 1),
        'max_pips': normal_range_pips,
        'is_reasonable': actual_pips <= normal_range_pips
    }
def format_price(asset: str, price: float) -> str:
    """Format price with correct decimals for display"""
    decimals = get_asset_params(asset)['decimals']
    return f"{price:.{decimals}f}"
