"""
Asset Class Risk Management
- Separate risk parameters for Forex, Metals, Indices, Commodities
- Dynamic position sizing per asset class
- Class-specific drawdown limits
- Risk budgeting across asset classes
"""

import json
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading


class AssetClass(Enum):
    FOREX = "forex"
    METALS = "metals"
    INDICES = "indices"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    BONDS = "bonds"


@dataclass
class RiskParameters:
    """Risk parameters for an asset class"""
    # Position limits
    max_position_pct: float = 0.10      # Max 10% of capital per asset class
    max_asset_position_pct: float = 0.05 # Max 5% per individual asset
    max_total_exposure_pct: float = 0.50 # Max 50% total portfolio exposure
    
    # Stop loss and take profit (as percentage)
    default_stop_loss_pct: float = 0.01   # 1% stop loss
    default_take_profit_pct: float = 0.02 # 2% take profit
    
    # Daily limits
    daily_loss_limit_pct: float = 0.02    # 2% daily loss limit
    weekly_loss_limit_pct: float = 0.05   # 5% weekly loss limit
    
    # Leverage
    max_leverage: float = 10.0
    recommended_leverage: float = 5.0
    
    # Correlation risk
    max_correlation_exposure: float = 0.30 # Max 30% from correlated assets
    
    # Volatility adjustments
    volatility_multiplier: float = 1.0     # Adjust position size based on volatility
    min_volatility: float = 0.005         # 0.5% minimum volatility
    max_volatility: float = 0.03          # 3% maximum volatility


# Default risk parameters for each asset class
ASSET_CLASS_PARAMS: Dict[AssetClass, RiskParameters] = {
    AssetClass.FOREX: RiskParameters(
        max_position_pct=0.15,
        max_asset_position_pct=0.08,
        default_stop_loss_pct=0.005,
        default_take_profit_pct=0.01,
        daily_loss_limit_pct=0.02,
        weekly_loss_limit_pct=0.05,
        max_leverage=30.0,
        recommended_leverage=10.0,
        volatility_multiplier=0.8
    ),
    AssetClass.METALS: RiskParameters(
        max_position_pct=0.10,
        max_asset_position_pct=0.05,
        default_stop_loss_pct=0.01,
        default_take_profit_pct=0.02,
        daily_loss_limit_pct=0.03,
        weekly_loss_limit_pct=0.08,
        max_leverage=20.0,
        recommended_leverage=5.0,
        volatility_multiplier=1.2
    ),
    AssetClass.INDICES: RiskParameters(
        max_position_pct=0.12,
        max_asset_position_pct=0.06,
        default_stop_loss_pct=0.01,
        default_take_profit_pct=0.02,
        daily_loss_limit_pct=0.02,
        weekly_loss_limit_pct=0.06,
        max_leverage=20.0,
        recommended_leverage=5.0,
        volatility_multiplier=1.0
    ),
    AssetClass.COMMODITIES: RiskParameters(
        max_position_pct=0.08,
        max_asset_position_pct=0.04,
        default_stop_loss_pct=0.015,
        default_take_profit_pct=0.03,
        daily_loss_limit_pct=0.04,
        weekly_loss_limit_pct=0.10,
        max_leverage=10.0,
        recommended_leverage=3.0,
        volatility_multiplier=1.5
    ),
    AssetClass.CRYPTO: RiskParameters(
        max_position_pct=0.05,
        max_asset_position_pct=0.03,
        default_stop_loss_pct=0.02,
        default_take_profit_pct=0.04,
        daily_loss_limit_pct=0.05,
        weekly_loss_limit_pct=0.15,
        max_leverage=5.0,
        recommended_leverage=2.0,
        volatility_multiplier=2.0
    ),
    AssetClass.BONDS: RiskParameters(
        max_position_pct=0.15,
        max_asset_position_pct=0.10,
        default_stop_loss_pct=0.003,
        default_take_profit_pct=0.006,
        daily_loss_limit_pct=0.015,
        weekly_loss_limit_pct=0.04,
        max_leverage=20.0,
        recommended_leverage=10.0,
        volatility_multiplier=0.6
    ),
}


class AssetClassMapper:
    """Maps assets to their respective asset classes"""
    
    def __init__(self):
        self.mappings = {
            # Forex
            'EURUSD': AssetClass.FOREX,
            'GBPUSD': AssetClass.FOREX,
            'USDJPY': AssetClass.FOREX,
            'AUDUSD': AssetClass.FOREX,
            'USDCAD': AssetClass.FOREX,
            'NZDUSD': AssetClass.FOREX,
            'USDCHF': AssetClass.FOREX,
            'EUR/GBP': AssetClass.FOREX,
            'EUR/JPY': AssetClass.FOREX,
            'GBP/JPY': AssetClass.FOREX,
            
            # Metals
            'XAU/USD': AssetClass.METALS,
            'XAG/USD': AssetClass.METALS,
            'XPT/USD': AssetClass.METALS,
            'XPD/USD': AssetClass.METALS,
            'GOLD': AssetClass.METALS,
            'SILVER': AssetClass.METALS,
            
            # Indices
            'S&P500/USD': AssetClass.INDICES,
            'NAS100/USD': AssetClass.INDICES,
            'DJ30/USD': AssetClass.INDICES,
            'GER30/EUR': AssetClass.INDICES,
            'UK100/GBP': AssetClass.INDICES,
            'JPN225/JPY': AssetClass.INDICES,
            'AUS200/AUD': AssetClass.INDICES,
            'S&P500': AssetClass.INDICES,
            'NASDAQ': AssetClass.INDICES,
            'DOW30': AssetClass.INDICES,
            
            # Commodities
            'BCO/USD': AssetClass.COMMODITIES,
            'WTICO/USD': AssetClass.COMMODITIES,
            'XCU/USD': AssetClass.COMMODITIES,
            'XNG/USD': AssetClass.COMMODITIES,
            'BRENT_OIL': AssetClass.COMMODITIES,
            'WTI_OIL': AssetClass.COMMODITIES,
            
            # Crypto (if you add later)
            'BTC/USD': AssetClass.CRYPTO,
            'ETH/USD': AssetClass.CRYPTO,
        }
        
        # Reverse mapping for display
        self.class_display_names = {
            AssetClass.FOREX: "💱 Forex",
            AssetClass.METALS: "🥇 Metals",
            AssetClass.INDICES: "📊 Indices",
            AssetClass.COMMODITIES: "🛢️ Commodities",
            AssetClass.CRYPTO: "₿ Crypto",
            AssetClass.BONDS: "📜 Bonds"
        }
    
    def get_asset_class(self, asset: str) -> AssetClass:
        """Get asset class for a given asset"""
        # Try exact match first
        if asset in self.mappings:
            return self.mappings[asset]
        
        # Try partial match
        for key, asset_class in self.mappings.items():
            if key in asset or asset in key:
                return asset_class
        
        # Default to FOREX
        return AssetClass.FOREX
    
    def get_display_name(self, asset_class: AssetClass) -> str:
        """Get display name for asset class"""
        return self.class_display_names.get(asset_class, "Unknown")


class AssetClassRiskManager:
    """
    Manages risk separately for each asset class.
    Tracks exposure, PnL, and limits per class.
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.params = ASSET_CLASS_PARAMS
        
        # Track per asset class
        self.class_exposure: Dict[AssetClass, float] = defaultdict(float)
        self.class_pnl: Dict[AssetClass, float] = defaultdict(float)
        self.class_daily_pnl: Dict[AssetClass, float] = defaultdict(float)
        self.class_weekly_pnl: Dict[AssetClass, float] = defaultdict(float)
        self.class_positions: Dict[AssetClass, List[Dict]] = defaultdict(list)
        
        # Track per asset
        self.asset_exposure: Dict[str, float] = defaultdict(float)
        self.asset_pnl: Dict[str, float] = defaultdict(float)
        
        # Daily reset tracking
        self.current_date = date.today()
        self.week_start = self._get_week_start()
        
        # Historical data
        self.history: List[Dict] = []
        self.lock = threading.Lock()
        
        # Load previous state
        self._load_state()
    
    def _get_week_start(self) -> date:
        """Get start of current week (Monday)"""
        today = date.today()
        return today - timedelta(days=today.weekday())
    
    def _reset_daily_if_needed(self):
        """Reset daily PnL at start of new day"""
        today = date.today()
        if today != self.current_date:
            self.class_daily_pnl = defaultdict(float)
            self.current_date = today
            
            # Check weekly reset
            week_start = self._get_week_start()
            if week_start != self.week_start:
                self.class_weekly_pnl = defaultdict(float)
                self.week_start = week_start
    
    def _save_state(self):
        """Save risk state to disk"""
        state = {
            'timestamp': datetime.now().isoformat(),
            'capital': self.capital,
            'class_pnl': {k.value: v for k, v in self.class_pnl.items()},
            'class_exposure': {k.value: v for k, v in self.class_exposure.items()},
            'history': self.history[-100:]  # Last 100 records
        }
        try:
            with open('risk_state.json', 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Failed to save risk state: {e}")
    
    def _load_state(self):
        """Load risk state from disk"""
        if os.path.exists('risk_state.json'):
            try:
                with open('risk_state.json', 'r') as f:
                    state = json.load(f)
                    self.capital = state.get('capital', self.initial_capital)
                    # Restore class PnL
                    for class_val, pnl in state.get('class_pnl', {}).items():
                        self.class_pnl[AssetClass(class_val)] = pnl
            except Exception as e:
                print(f"Failed to load risk state: {e}")
    
    def update_capital(self, new_capital: float):
        """Update total capital"""
        self.capital = new_capital
        self._save_state()
    
    def get_risk_params(self, asset: str) -> RiskParameters:
        """Get risk parameters for an asset"""
        asset_class = AssetClassMapper().get_asset_class(asset)
        return self.params.get(asset_class, RiskParameters())
    
    def get_asset_class(self, asset: str) -> AssetClass:
        """Get asset class for an asset"""
        return AssetClassMapper().get_asset_class(asset)
    
    def calculate_position_size(self, asset: str, confidence: float, 
                                 volatility: float, atr: float) -> Dict:
        """
        Calculate maximum allowed position size based on risk parameters.
        """
        asset_class = self.get_asset_class(asset)
        params = self.params[asset_class]
        
        # Base size from confidence
        base_size = confidence / 100 * params.max_asset_position_pct
        
        # Adjust for volatility
        vol_ratio = max(params.min_volatility, min(params.max_volatility, volatility))
        vol_adjustment = params.volatility_multiplier * (params.min_volatility / vol_ratio)
        
        # Adjust for current exposure
        current_class_exposure = self.class_exposure[asset_class] / self.capital
        remaining_capacity = max(0, params.max_position_pct - current_class_exposure)
        
        # Current asset exposure
        current_asset_exposure = self.asset_exposure[asset] / self.capital
        remaining_asset_capacity = max(0, params.max_asset_position_pct - current_asset_exposure)
        
        # Check daily loss limits
        daily_loss_pct = self.class_daily_pnl[asset_class] / self.capital
        if daily_loss_pct <= -params.daily_loss_limit_pct:
            return {
                'allowed': False,
                'reason': f"Daily loss limit reached for {asset_class.value}: {daily_loss_pct:.2%}",
                'position_pct': 0
            }
        
        # Check weekly loss limits
        weekly_loss_pct = self.class_weekly_pnl[asset_class] / self.capital
        if weekly_loss_pct <= -params.weekly_loss_limit_pct:
            return {
                'allowed': False,
                'reason': f"Weekly loss limit reached for {asset_class.value}: {weekly_loss_pct:.2%}",
                'position_pct': 0
            }
        
        # Final position size
        raw_size = base_size * vol_adjustment
        final_size = min(raw_size, remaining_capacity, remaining_asset_capacity, params.max_asset_position_pct)
        
        return {
            'allowed': final_size > 0.005,  # Minimum 0.5% position
            'position_pct': round(final_size * 100, 2),
            'position_value': round(self.capital * final_size, 2),
            'asset_class': asset_class.value,
            'max_allowed_pct': params.max_asset_position_pct * 100,
            'current_exposure_pct': round(current_class_exposure * 100, 2),
            'remaining_capacity_pct': round(remaining_capacity * 100, 2),
            'volatility_adjustment': round(vol_adjustment, 2),
            'reason': f"Position size: {final_size*100:.2f}% of capital"
        }
    
    def record_trade_entry(self, asset: str, position_size: float, 
                           entry_price: float, direction: str):
        """Record a new trade entry"""
        asset_class = self.get_asset_class(asset)
        position_value = position_size * entry_price
        
        with self.lock:
            self.class_exposure[asset_class] += position_value
            self.asset_exposure[asset] += position_value
            
            self.class_positions[asset_class].append({
                'asset': asset,
                'size': position_size,
                'entry_price': entry_price,
                'direction': direction,
                'timestamp': datetime.now().isoformat()
            })
            
            self._save_state()
    
    def record_trade_exit(self, asset: str, position_size: float, 
                          exit_price: float, pnl: float):
        """Record a trade exit and update PnL"""
        asset_class = self.get_asset_class(asset)
        
        with self.lock:
            # Update PnL
            self.class_pnl[asset_class] += pnl
            self.class_daily_pnl[asset_class] += pnl
            self.class_weekly_pnl[asset_class] += pnl
            self.asset_pnl[asset] += pnl
            
            # Update exposure
            position_value = position_size * exit_price
            self.class_exposure[asset_class] = max(0, self.class_exposure[asset_class] - position_value)
            self.asset_exposure[asset] = max(0, self.asset_exposure[asset] - position_value)
            
            # Update total capital
            self.capital += pnl
            self._save_state()
            
            # Record history
            self.history.append({
                'timestamp': datetime.now().isoformat(),
                'asset': asset,
                'asset_class': asset_class.value,
                'pnl': pnl,
                'capital': self.capital
            })
    
    def get_class_status(self, asset_class: AssetClass) -> Dict:
        """Get risk status for a specific asset class"""
        params = self.params[asset_class]
        
        return {
            'asset_class': asset_class.value,
            'display_name': AssetClassMapper().get_display_name(asset_class),
            'exposure_pct': round(self.class_exposure[asset_class] / self.capital * 100, 2),
            'max_exposure_pct': params.max_position_pct * 100,
            'daily_pnl_pct': round(self.class_daily_pnl[asset_class] / self.capital * 100, 2),
            'daily_limit_pct': params.daily_loss_limit_pct * 100,
            'weekly_pnl_pct': round(self.class_weekly_pnl[asset_class] / self.capital * 100, 2),
            'weekly_limit_pct': params.weekly_loss_limit_pct * 100,
            'total_pnl': self.class_pnl[asset_class],
            'positions_count': len(self.class_positions[asset_class]),
            'can_trade': self.class_daily_pnl[asset_class] / self.capital > -params.daily_loss_limit_pct
        }
    
    def get_all_class_status(self) -> Dict:
        """Get risk status for all asset classes"""
        return {
            'total_capital': self.capital,
            'initial_capital': self.initial_capital,
            'total_return_pct': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'classes': {ac.value: self.get_class_status(ac) for ac in AssetClass}
        }
    
    def get_overall_status(self) -> Dict:
        """Get overall risk status"""
        total_exposure = sum(self.class_exposure.values())
        total_pnl = sum(self.class_pnl.values())
        
        # Check if any class has reached limit
        blocked_classes = []
        for ac in AssetClass:
            if self.class_daily_pnl[ac] / self.capital <= -self.params[ac].daily_loss_limit_pct:
                blocked_classes.append(ac.value)
        
        return {
            'total_capital': self.capital,
            'total_exposure_pct': round(total_exposure / self.capital * 100, 2),
            'total_pnl': total_pnl,
            'total_return_pct': round((self.capital - self.initial_capital) / self.initial_capital * 100, 2),
            'blocked_classes': blocked_classes,
            'can_trade_any': len(blocked_classes) < len(AssetClass),
            'active_positions': sum(len(positions) for positions in self.class_positions.values())
        }
    
    def can_trade_asset(self, asset: str) -> Tuple[bool, str, Dict]:
        """Check if trading is allowed for an asset"""
        asset_class = self.get_asset_class(asset)
        params = self.params[asset_class]
        
        # Check class daily limit
        daily_loss_pct = self.class_daily_pnl[asset_class] / self.capital
        if daily_loss_pct <= -params.daily_loss_limit_pct:
            return False, f"Daily loss limit reached for {asset_class.value}", self.get_class_status(asset_class)
        
        # Check class exposure
        current_exposure = self.class_exposure[asset_class] / self.capital
        if current_exposure >= params.max_position_pct:
            return False, f"Max exposure reached for {asset_class.value}", self.get_class_status(asset_class)
        
        # Check asset exposure
        current_asset_exposure = self.asset_exposure[asset] / self.capital
        if current_asset_exposure >= params.max_asset_position_pct:
            return False, f"Max exposure reached for {asset}", self.get_class_status(asset_class)
        
        return True, "Trading allowed", self.get_class_status(asset_class)
    
    def reset_daily(self):
        """Reset daily PnL (called at market close)"""
        self.class_daily_pnl = defaultdict(float)
        self._save_state()
        print("✅ Daily risk limits reset")


# ============================================================
# Integration with Trading System
# ============================================================

class RiskAwareTrader:
    """
    Wrapper that integrates risk management with trading decisions.
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.risk_manager = AssetClassRiskManager(initial_capital)
    
    def get_trade_decision(self, asset: str, signal: str, confidence: float,
                           price: float, volatility: float, atr: float) -> Dict:
        """Get risk-adjusted trade decision"""
        
        # Check if trading is allowed
        can_trade, reason, class_status = self.risk_manager.can_trade_asset(asset)
        
        if not can_trade:
            return {
                'execute': False,
                'reason': reason,
                'position_size': 0,
                'class_status': class_status
            }
        
        # Calculate position size
        position_result = self.risk_manager.calculate_position_size(
            asset, confidence, volatility, atr
        )
        
        if not position_result['allowed']:
            return {
                'execute': False,
                'reason': position_result['reason'],
                'position_size': 0,
                'class_status': class_status
            }
        
        # Get risk parameters for stop loss and take profit
        params = self.risk_manager.get_risk_params(asset)
        
        if signal == 'BUY':
            stop_loss = price * (1 - params.default_stop_loss_pct)
            take_profit = price * (1 + params.default_take_profit_pct)
        else:
            stop_loss = price * (1 + params.default_stop_loss_pct)
            take_profit = price * (1 - params.default_take_profit_pct)
        
        return {
            'execute': True,
            'position_size': position_result['position_pct'],
            'position_value': position_result['position_value'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'asset_class': position_result['asset_class'],
            'max_exposure': position_result['max_allowed_pct'],
            'current_exposure': position_result['current_exposure_pct'],
            'reason': position_result['reason']
        }
    
    def record_entry(self, asset: str, position_size: float, entry_price: float, direction: str):
        """Record trade entry"""
        self.risk_manager.record_trade_entry(asset, position_size, entry_price, direction)
    
    def record_exit(self, asset: str, position_size: float, exit_price: float, pnl: float):
        """Record trade exit"""
        self.risk_manager.record_trade_exit(asset, position_size, exit_price, pnl)
    
    def get_risk_report(self) -> str:
        """Get formatted risk report for Telegram"""
        all_status = self.risk_manager.get_all_class_status()
        overall = self.risk_manager.get_overall_status()
        
        report = f"""
📊 *RISK MANAGEMENT REPORT*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 *PORTFOLIO*
   Capital: ${overall['total_capital']:,.2f}
   Return: {overall['total_return_pct']:.2f}%
   Exposure: {overall['total_exposure_pct']}%
   Active Positions: {overall['active_positions']}

📋 *ASSET CLASS BREAKDOWN*
"""
        for class_key, class_data in all_status['classes'].items():
            if class_data['exposure_pct'] > 0 or class_data['total_pnl'] != 0:
                status_emoji = "🟢" if class_data['can_trade'] else "🔴"
                report += f"""
{status_emoji} *{class_data['display_name']}*
   Exposure: {class_data['exposure_pct']}% / {class_data['max_exposure_pct']}%
   Daily PnL: {class_data['daily_pnl_pct']:.2f}% / {class_data['daily_limit_pct']}%
   Total PnL: ${class_data['total_pnl']:.2f}
   Positions: {class_data['positions_count']}
"""
        
        if overall['blocked_classes']:
            report += f"\n⚠️ *BLOCKED CLASSES:* {', '.join(overall['blocked_classes'])}"
        
        return report


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("ASSET CLASS RISK MANAGEMENT - TEST")
    print("=" * 60)
    
    # Create risk manager
    risk_manager = AssetClassRiskManager(initial_capital=100000)
    
    # Test position sizing for different asset classes
    test_cases = [
        ('EURUSD', 'FOREX', 85, 0.008, 0.0008),
        ('XAU/USD', 'METALS', 80, 0.015, 0.0015),
        ('S&P500/USD', 'INDICES', 75, 0.012, 0.0012),
        ('BCO/USD', 'COMMODITIES', 70, 0.02, 0.002),
    ]
    
    print("\n📊 Position Sizing Tests:")
    for asset, class_name, confidence, vol, atr in test_cases:
        result = risk_manager.calculate_position_size(asset, confidence, vol, atr)
        print(f"\n   {asset} ({class_name})")
        print(f"      Confidence: {confidence}%")
        print(f"      Allowed: {result['allowed']}")
        print(f"      Position: {result['position_pct']}% (${result['position_value']:,.0f})")
        print(f"      Reason: {result['reason']}")
    
    # Simulate trades
    print("\n" + "=" * 60)
    print("SIMULATING TRADES")
    print("=" * 60)
    
    # Enter a Forex trade
    risk_manager.record_trade_entry('EURUSD', 50000, 1.0950, 'BUY')
    
    # Check status
    status = risk_manager.get_class_status(AssetClass.FOREX)
    print(f"\n📊 Forex Class Status:")
    print(f"   Exposure: {status['exposure_pct']}%")
    print(f"   Daily PnL: {status['daily_pnl_pct']}%")
    
    # Exit with profit
    risk_manager.record_trade_exit('EURUSD', 50000, 1.1000, 250)
    
    # Final report
    trader = RiskAwareTrader(100000)
    print("\n" + trader.get_risk_report())
    
    print("\n✅ Asset class risk management ready")
