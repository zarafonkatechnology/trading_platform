"""
5-Minute Cycle Manager - Runs RL training every 5 minutes
"""

import threading
import time
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class TrainingCycleManager:
    """
    Manages RL training cycles every 5 minutes:
    1. Engineer features from latest market data
    2. Agents take actions based on state
    3. Calculate rewards based on outcomes
    4. Mini-batch update to database
    """
    
    def __init__(self, agents: List, feature_engineer, db_manager):
        self.agents = agents
        self.feature_engineer = feature_engineer
        self.db = db_manager
        self.cycle_number = 0
        self.is_running = False
        self.cycle_thread = None
    
    def start(self):
        """Start the 5-minute training cycle"""
        self.is_running = True
        self.cycle_thread = threading.Thread(target=self._cycle_loop, daemon=True)
        self.cycle_thread.start()
        print("🔄 RL Training Cycle started (every 5 minutes)")
    
    def _cycle_loop(self):
        """Main training loop - runs every 5 minutes"""
        while self.is_running:
            try:
                self.cycle_number += 1
                cycle_start = datetime.now()
                
                print(f"\n{'='*60}")
                print(f"🧠 RL TRAINING CYCLE #{self.cycle_number} at {cycle_start.strftime('%H:%M:%S')}")
                print(f"{'='*60}")
                
                # Run training for all agents
                for agent in self.agents:
                    self._train_agent(agent)
                
                cycle_end = datetime.now()
                duration = (cycle_end - cycle_start).total_seconds()
                
                self._store_cycle_metrics(cycle_start, cycle_end, duration)
                
                print(f"✅ Cycle #{self.cycle_number} completed in {duration:.1f}s")
                
                # Wait for next cycle (5 minutes)
                time.sleep(300 - duration)
                
            except Exception as e:
                logger.error(f"Training cycle error: {e}")
                time.sleep(60)
    
    def _train_agent(self, agent):
        """Train a single agent using experience replay"""
        if len(agent.memory) < 10:
            print(f"  {agent.name}: Not enough experiences ({len(agent.memory)}/10)")
            return
        
        loss = agent.mini_batch_update(batch_size=32)
        stats = agent.get_stats()
        
        print(f"  {agent.name}: Loss={loss:.3f}, Q-size={stats['q_table_size']}, "
              f"Exploration={stats['exploration_rate']:.2f}, Win Rate={stats['win_rate']}%")
    
    def _store_cycle_metrics(self, start_time: datetime, end_time: datetime, duration: float):
        """Store cycle metrics in database"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            for agent in self.agents:
                stats = agent.get_stats()
                cursor.execute("""
                    INSERT INTO rl_cycle_metrics 
                    (cycle_number, start_time, end_time, agent_name, avg_reward, 
                     total_xp, action_distribution, processed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    self.cycle_number, start_time, end_time, agent.name,
                    stats['total_reward'], 0, '{}', 1
                ))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not store cycle metrics: {e}")
    
    def stop(self):
        """Stop training cycle"""
        self.is_running = False
        if self.cycle_thread:
            self.cycle_thread.join(timeout=2)
        print("🛑 RL Training Cycle stopped")
