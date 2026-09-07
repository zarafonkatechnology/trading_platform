# ============================================================
# final_evaluation.py - Complete System Evaluation
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔍 COMPLETE SYSTEM EVALUATION")
    print("=" * 70)
    print()
    
    # 1. Initialize components
    performance = PerformanceMetrics()
    improvement_engine = ImprovementEngine(performance)
    
    # 2. Load or simulate trade history
    # For demonstration, simulate some trades
    import random
    
    for i in range(50):
        trade = {
            'entry_time': datetime.now() - timedelta(minutes=i*5),
            'exit_time': datetime.now() - timedelta(minutes=i*5 - random.randint(2, 10)),
            'entry_price': 6000 + random.uniform(-50, 50),
            'exit_price': 6000 + random.uniform(-50, 50),
            'quantity': 0.02,
            'pnl': random.choice([100, 120, 80, 90, 70, -50, -30, -80, 110]),
            'entry_z': random.uniform(2.5, 4.0),
            'exit_z': random.uniform(-0.5, 0.5),
            'hold_minutes': random.uniform(3, 15),
            'symbol': '#S&P500',
            'signal': 'BUY' if random.random() > 0.5 else 'SELL'
        }
        performance.add_trade(trade)
    
    # 3. Print comprehensive report
    performance.print_report()
    
    # 4. Generate recommendations
    print()
    recommendations = improvement_engine.analyze()
    improvement_engine.print_recommendations()
    
    # 5. Save results
    report = performance.get_comprehensive_report()
    with open('performance_report.json', 'w') as f:
        json.dump(report, f, default=str, indent=2)
    
    print("\n💾 Report saved to performance_report.json")