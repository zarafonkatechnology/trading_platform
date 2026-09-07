"""
Feature Store for RLHF
- Automatically logs every market state, agent vote, and outcome
- Stores features, actions, rewards, and metadata
- Provides query interface for training data
- Supports time-based windowing and filtering
"""

import sqlite3
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import os


@dataclass
class FeatureRecord:
    """Single record in feature store."""
    timestamp: datetime
    asset: str
    market_features: Dict  # RSI, volume_ratio, volatility, etc.
    agent_votes: Dict      # Each agent's vote and confidence
    consensus_action: str  # BUY/SELL/HOLD
    consensus_confidence: float
    actual_outcome: Optional[float] = None  # PnL after trade
    actual_action: Optional[str] = None      # What actually happened
    reward: Optional[float] = None
    episode_id: Optional[int] = None
    metadata: Optional[Dict] = None


class FeatureStore:
    """
    SQLite-based feature store for RLHF training data.
    Automatically logs market states, agent votes, and outcomes.
    """
    
    def __init__(self, db_path: str = "feature_store.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main features table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS features (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    asset TEXT NOT NULL,
                    episode_id INTEGER,
                    
                    -- Market features
                    price REAL,
                    rsi REAL,
                    volume_ratio REAL,
                    volatility REAL,
                    supply_distance REAL,
                    demand_distance REAL,
                    manipulation_score REAL,
                    zone_strength REAL,
                    touches INTEGER,
                    hidden_funds_estimate REAL,
                    
                    -- Additional market data
                    regime TEXT,
                    adx REAL,
                    trend_direction TEXT,
                    
                    -- Consensus
                    consensus_action TEXT,
                    consensus_confidence REAL,
                    
                    -- Agent votes (stored as JSON)
                    agent_votes_json TEXT,
                    
                    -- Outcomes
                    actual_action TEXT,
                    actual_outcome REAL,
                    reward REAL,
                    
                    -- Metadata
                    metadata_json TEXT,
                    
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Agent performance table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    total_votes INTEGER,
                    win_rate REAL,
                    avg_confidence REAL,
                    xp_points INTEGER,
                    token_balance INTEGER
                )
            ''')
            
            # Episodes table (for RL training episodes)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    asset TEXT,
                    total_steps INTEGER,
                    total_reward REAL,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Create indexes for faster queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON features(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_asset ON features(asset)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_episode ON features(episode_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_consensus ON features(consensus_action)')
            
            conn.commit()
            print("✅ Feature store database initialized")
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def start_episode(self, asset: str) -> int:
        """Start a new training episode."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO episodes (start_time, asset, status)
                VALUES (?, ?, ?)
            ''', (datetime.now().isoformat(), asset, 'active'))
            conn.commit()
            return cursor.lastrowid
    
    def end_episode(self, episode_id: int, total_reward: float):
        """End an episode with total reward."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE episodes 
                SET end_time = ?, total_reward = ?, status = 'completed'
                WHERE id = ?
            ''', (datetime.now().isoformat(), total_reward, episode_id))
            conn.commit()
    
    def log_market_state(self, asset: str, features: Dict, consensus: Dict,
                          agent_votes: Dict, episode_id: Optional[int] = None) -> int:
        """
        Log a complete market state with agent votes.
        
        Args:
            asset: Asset symbol
            features: Market features dictionary
            consensus: Consensus decision with confidence
            agent_votes: Dictionary of agent_name -> {'vote': str, 'confidence': float}
            episode_id: Optional episode ID for RL training
        
        Returns:
            Record ID of inserted row
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Extract market features
            rsi = features.get('rsi')
            volume_ratio = features.get('volume_ratio')
            volatility = features.get('volatility')
            supply_distance = features.get('supply_distance')
            demand_distance = features.get('demand_distance')
            manipulation_score = features.get('manipulation_score')
            zone_strength = features.get('zone_strength')
            touches = features.get('touches')
            hidden_funds = features.get('hidden_funds_estimate')
            price = features.get('price')
            regime = features.get('regime')
            adx = features.get('adx')
            trend_direction = features.get('trend_direction')
            
            # Extract consensus
            consensus_action = consensus.get('signal', 'HOLD')
            consensus_confidence = consensus.get('confidence', 0)
            
            # Convert agent votes to JSON
            agent_votes_json = json.dumps(agent_votes)
            
            cursor.execute('''
                INSERT INTO features (
                    timestamp, asset, episode_id,
                    price, rsi, volume_ratio, volatility,
                    supply_distance, demand_distance, manipulation_score,
                    zone_strength, touches, hidden_funds_estimate,
                    regime, adx, trend_direction,
                    consensus_action, consensus_confidence,
                    agent_votes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(), asset, episode_id,
                price, rsi, volume_ratio, volatility,
                supply_distance, demand_distance, manipulation_score,
                zone_strength, touches, hidden_funds,
                regime, adx, trend_direction,
                consensus_action, consensus_confidence,
                agent_votes_json
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def log_outcome(self, record_id: int, actual_action: str, pnl: float, reward: float):
        """
        Update a record with actual outcome after trade closes.
        
        Args:
            record_id: ID from log_market_state
            actual_action: What actually happened (BUY/SELL/HOLD)
            pnl: Profit/loss percentage
            reward: Calculated reward for RL
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE features 
                SET actual_action = ?, actual_outcome = ?, reward = ?
                WHERE id = ?
            ''', (actual_action, pnl, reward, record_id))
            conn.commit()
    
    def log_agent_performance(self, agent_name: str, metrics: Dict):
        """Log agent performance metrics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_performance (
                    agent_name, timestamp, total_votes, win_rate, 
                    avg_confidence, xp_points, token_balance
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_name, datetime.now().isoformat(),
                metrics.get('total_votes', 0),
                metrics.get('win_rate', 0),
                metrics.get('avg_confidence', 0),
                metrics.get('xp_points', 0),
                metrics.get('token_balance', 0)
            ))
            conn.commit()
    
    def get_training_data(self, 
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          asset: Optional[str] = None,
                          min_confidence: float = 0.0,
                          only_completed: bool = True,
                          limit: int = 10000) -> pd.DataFrame:
        """
        Retrieve training data for RLHF.
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            asset: Asset filter
            min_confidence: Minimum consensus confidence
            only_completed: Only include records with outcomes
            limit: Maximum number of records
        
        Returns:
            DataFrame with features, actions, and rewards
        """
        query = "SELECT * FROM features WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date.isoformat())
        
        if asset:
            query += " AND asset = ?"
            params.append(asset)
        
        if only_completed:
            query += " AND actual_outcome IS NOT NULL"
        
        if min_confidence > 0:
            query += " AND consensus_confidence >= ?"
            params.append(min_confidence)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            
            # Parse JSON columns
            if 'agent_votes_json' in df.columns:
                df['agent_votes'] = df['agent_votes_json'].apply(json.loads)
            
            return df
    
    def get_expert_dataset(self, min_confidence: float = 70, 
                           min_trades: int = 10) -> pd.DataFrame:
        """
        Get expert dataset for HA3C pretraining.
        Only includes high-confidence trades with outcomes.
        """
        df = self.get_training_data(
            min_confidence=min_confidence / 100,
            only_completed=True
        )
        
        if len(df) < min_trades:
            print(f"⚠️ Only {len(df)} expert examples available (need {min_trades})")
        
        return df
    
    def get_recent_performance(self, hours: int = 24) -> Dict:
        """Get recent performance metrics."""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        df = self.get_training_data(
            start_date=cutoff,
            only_completed=True
        )
        
        if df.empty:
            return {'status': 'No data', 'samples': 0}
        
        # Calculate metrics
        total_trades = len(df)
        winning_trades = len(df[df['actual_outcome'] > 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        total_pnl = df['actual_outcome'].sum()
        avg_reward = df['reward'].mean() if 'reward' in df.columns else 0
        
        # Action distribution
        action_dist = df['consensus_action'].value_counts().to_dict()
        
        return {
            'status': 'Active',
            'samples': total_trades,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 4),
            'avg_reward': round(avg_reward, 4),
            'action_distribution': action_dist,
            'period_hours': hours
        }
    
    def export_to_csv(self, output_path: str, **filters):
        """Export training data to CSV."""
        df = self.get_training_data(**filters)
        df.to_csv(output_path, index=False)
        print(f"✅ Exported {len(df)} records to {output_path}")
    
    def get_stats(self) -> Dict:
        """Get feature store statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM features")
            total_records = cursor.fetchone()[0]
            
            # Records with outcomes
            cursor.execute("SELECT COUNT(*) FROM features WHERE actual_outcome IS NOT NULL")
            completed_records = cursor.fetchone()[0]
            
            # Unique assets
            cursor.execute("SELECT COUNT(DISTINCT asset) FROM features")
            unique_assets = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM features")
            min_date, max_date = cursor.fetchone()
            
            # Total episodes
            cursor.execute("SELECT COUNT(*) FROM episodes")
            total_episodes = cursor.fetchone()[0]
            
            return {
                'total_records': total_records,
                'completed_records': completed_records,
                'unique_assets': unique_assets,
                'date_range': {
                    'start': min_date,
                    'end': max_date
                },
                'total_episodes': total_episodes,
                'completion_rate': round(completed_records / total_records * 100, 1) if total_records > 0 else 0
            }


# ============================================================
# Integration Helper
# ============================================================

class RLHFFeatureCollector:
    """
    Helper class to automatically collect features during trading.
    Integrates with your existing trading loop.
    """
    
    def __init__(self, feature_store: FeatureStore):
        self.store = feature_store
        self.current_episode_id = None
        self.current_asset = None
        self.record_id = None
    
    def start_trading_session(self, asset: str):
        """Start a new trading session/episode."""
        self.current_asset = asset
        self.current_episode_id = self.store.start_episode(asset)
        print(f"📊 Started episode {self.current_episode_id} for {asset}")
    
    def end_trading_session(self):
        """End current trading session."""
        if self.current_episode_id:
            self.store.end_episode(self.current_episode_id, 0)  # Total reward will be updated later
            self.current_episode_id = None
    
    def record_state(self, features: Dict, consensus: Dict, agent_votes: Dict):
        """Record current market state and agent decisions."""
        self.record_id = self.store.log_market_state(
            asset=self.current_asset,
            features=features,
            consensus=consensus,
            agent_votes=agent_votes,
            episode_id=self.current_episode_id
        )
        return self.record_id
    
    def record_outcome(self, actual_action: str, pnl: float, reward: float):
        """Record outcome after trade closes."""
        if self.record_id:
            self.store.log_outcome(self.record_id, actual_action, pnl, reward)


# ============================================================
# Test
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("FEATURE STORE - TEST")
    print("=" * 60)
    
    # Initialize feature store
    store = FeatureStore("test_feature_store.db")
    
    # Clear previous data for testing
    if os.path.exists("test_feature_store.db"):
        os.remove("test_feature_store.db")
        store = FeatureStore("test_feature_store.db")
    
    # Test logging
    print("\n📝 Logging test data...")
    
    # Simulate a trading session
    collector = RLHFFeatureCollector(store)
    collector.start_trading_session("EURUSD")
    
    for i in range(10):
        # Simulate market features
        features = {
            'price': 1.0950 + np.random.normal(0, 0.0005),
            'rsi': 55 + np.random.normal(0, 5),
            'volume_ratio': 1.2 + np.random.normal(0, 0.2),
            'volatility': 0.008 + np.random.normal(0, 0.001),
            'supply_distance': 0.005 + abs(np.random.normal(0, 0.002)),
            'demand_distance': 0.003 + abs(np.random.normal(0, 0.002)),
            'manipulation_score': 0.65 + np.random.normal(0, 0.1),
            'zone_strength': 70 + np.random.randint(-10, 10),
            'touches': np.random.randint(1, 5),
            'hidden_funds_estimate': 45000 + np.random.randint(-10000, 10000),
            'regime': np.random.choice(['TRENDING', 'RANGING', 'MIXED']),
            'adx': 25 + np.random.normal(0, 10),
            'trend_direction': np.random.choice(['UP', 'DOWN', 'SIDEWAYS'])
        }
        
        # Simulate consensus
        actions = ['BUY', 'SELL', 'HOLD']
        consensus = {
            'signal': np.random.choice(actions, p=[0.3, 0.3, 0.4]),
            'confidence': 65 + np.random.normal(0, 15)
        }
        consensus['confidence'] = min(98, max(50, consensus['confidence']))
        
        # Simulate agent votes
        agent_votes = {}
        for agent in ['Agent_A', 'Agent_B', 'Agent_C', 'Agent_D']:
            agent_votes[agent] = {
                'vote': np.random.choice(actions),
                'confidence': 60 + np.random.normal(0, 20)
            }
        
        # Record state
        collector.record_state(features, consensus, agent_votes)
        
        # Simulate outcome for some records
        if i % 3 == 0 and i > 0:
            pnl = np.random.normal(0, 0.02)
            reward = pnl * 100 * (consensus['confidence'] / 100)
            collector.record_outcome(consensus['signal'], pnl, reward)
    
    collector.end_trading_session()
    
    # Get stats
    print("\n📊 Feature Store Statistics:")
    stats = store.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Get training data
    print("\n📈 Training Data Sample:")
    df = store.get_training_data(limit=5)
    print(df[['asset', 'consensus_action', 'consensus_confidence', 'actual_outcome']].head())
    
    # Get recent performance
    print("\n🎯 Recent Performance:")
    perf = store.get_recent_performance(hours=1)
    for key, value in perf.items():
        print(f"   {key}: {value}")
    
    # Export to CSV
    store.export_to_csv("test_expert_dataset.csv", only_completed=True, limit=20)
    
    print("\n✅ Feature store test complete")
