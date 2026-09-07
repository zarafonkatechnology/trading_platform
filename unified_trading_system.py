# unified_trading_system.py
"""
Complete Unified AI Trading System
"""

class UnifiedTradingSystem:
    def __init__(self):
        self.mt4 = get_mt4_prices()
        self.price_cache = price_cache
        self.pipeline = AgentDeliberativePipeline()
        self.order_flow = OrderFlowAnalyzer()
        self.telegram = TelegramBot()
        
    def run(self):
        """Main execution loop"""
        
        while True:
            try:
                # 1. Get fresh prices
                prices = self.get_all_prices()
                
                for symbol, price in prices.items():
                    
                    # 2. Order flow analysis (fast)
                    flow_signal = self.order_flow.get_order_flow_signal(symbol, price)
                    
                    # 3. Agent deliberative pipeline (deep)
                    agent_result = self.pipeline.analyze_symbol(symbol, price)
                    
                    # 4. Combine signals
                    final_signal = self.combine_signals(flow_signal, agent_result)
                    
                    # 5. Risk check
                    if self.pass_risk_checks(symbol, final_signal):
                        
                        # 6. Execute or alert
                        if final_signal['confidence'] >= 85:
                            self.execute_trade(symbol, final_signal)
                            self.telegram.send_signal(final_signal, 'EXECUTED')
                        elif final_signal['confidence'] >= 70:
                            self.telegram.send_signal(final_signal, 'ALERT')
                    
                    # 7. Log everything
                    self.log_analysis(symbol, price, flow_signal, agent_result, final_signal)
                
                # 8. Wait for next cycle
                time.sleep(120)  # 2 minutes
                
            except Exception as e:
                print(f"System error: {e}")
                self.telegram.send_alert(f"⚠️ System error: {e}")
                time.sleep(60)
    
    def combine_signals(self, flow: dict, agent: dict) -> dict:
        """Combine order flow and agent signals"""
        
        flow_weight = 0.3
        agent_weight = 0.7
        
        # Convert to numeric scores
        flow_score = flow['score']
        agent_score = agent.get('score', 0)
        
        final_score = (flow_score * flow_weight) + (agent_score * agent_weight)
        
        return {
            'decision': 'BUY' if final_score > 25 else 'SELL' if final_score < -25 else 'HOLD',
            'confidence': min(95, abs(final_score)),
            'score': final_score,
            'flow_signals': flow['signals'],
            'agent_consensus': agent.get('decision', 'HOLD')
        }