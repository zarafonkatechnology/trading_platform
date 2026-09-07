# ============================================================
# improvement_recommendations.py - Auto-Improvement Engine
# ============================================================

class ImprovementEngine:
    """
    Analyzes performance and recommends specific improvements.
    """
    
    def __init__(self, performance: PerformanceMetrics):
        self.performance = performance
        self.recommendations = []
        
    def analyze(self):
        """Generate improvement recommendations."""
        self.recommendations = []
        
        # 1. Check expectancy
        expectancy = self.performance.get_expectancy()
        if expectancy['expectancy'] < 0.5:
            self.recommendations.append({
                'priority': 'HIGH',
                'area': 'Expectancy',
                'issue': f"Expectancy is ${expectancy['expectancy']:.2f} (target > $0.50)",
                'suggestion': 'Increase Z-score entry threshold to 3.0 OR reduce position size'
            })
        
        # 2. Check profit factor
        pf = self.performance.get_profit_factor()
        if pf['profit_factor'] < 1.3:
            self.recommendations.append({
                'priority': 'HIGH',
                'area': 'Profit Factor',
                'issue': f"Profit Factor is {pf['profit_factor']:.2f} (target > 1.3)",
                'suggestion': 'Add a trailing stop-loss OR tighten exit threshold to 0.3'
            })
        
        # 3. Check win rate
        if expectancy['win_rate'] < 50:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'area': 'Win Rate',
                'issue': f"Win Rate is {expectancy['win_rate']}%",
                'suggestion': 'Consider increasing entry threshold to 3.0 for higher quality signals'
            })
        
        # 4. Check execution quality
        eq = self.performance.get_execution_quality()
        if eq['avg_z_delta'] > 0.5:
            self.recommendations.append({
                'priority': 'MEDIUM',
                'area': 'Execution Quality',
                'issue': f"Avg Z-Delta is {eq['avg_z_delta']:.3f} (target < 0.5)",
                'suggestion': 'Improve execution speed OR enter at market instead of limit orders'
            })
        
        # 5. Check adverse moves
        if eq['adverse_percentage'] > 20:
            self.recommendations.append({
                'priority': 'HIGH',
                'area': 'Adverse Moves',
                'issue': f"Adverse moves in {eq['adverse_percentage']}% of trades",
                'suggestion': 'Add correlation protection OR reduce hold time to < 5 minutes'
            })
        
        # 6. Check drawdown
        calmar = self.performance.get_calmar_ratio()
        if calmar['max_drawdown'] > 15:
            self.recommendations.append({
                'priority': 'HIGH',
                'area': 'Drawdown',
                'issue': f"Max Drawdown is {calmar['max_drawdown']}%",
                'suggestion': 'Add daily loss limit (e.g., 5% max per day)'
            })
        
        return self.recommendations
    
    def print_recommendations(self):
        """Print all recommendations in priority order."""
        if not self.recommendations:
            print("✅ No improvements needed - System is performing well!")
            return
        
        print("=" * 70)
        print("📋 IMPROVEMENT RECOMMENDATIONS")
        print("=" * 70)
        print()
        
        # Sort by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        sorted_recs = sorted(self.recommendations, key=lambda x: priority_order.get(x['priority'], 3))
        
        for rec in sorted_recs:
            print(f"🔴 {rec['priority']} PRIORITY - {rec['area']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Suggestion: {rec['suggestion']}")
            print()
        
        print("=" * 70)