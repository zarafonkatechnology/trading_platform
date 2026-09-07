# database_manager.py
"""
PostgreSQL Database Manager for Agent Performance
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List

class DatabaseManager:
    def __init__(self, host='localhost', database='trading_db', user='postgres', password='password'):
        self.conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Create tables if they don't exist"""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS agent_performance (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR(50),
                symbol VARCHAR(20),
                vote VARCHAR(10),
                actual_result VARCHAR(10),
                confidence INT,
                xp INT,
                tokens INT,
                correct BOOLEAN,
                reasoning TEXT,
                deepseek_feedback TEXT,
                trade_pnl DECIMAL(10,2),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS agent_rankings (
                agent_name VARCHAR(50) PRIMARY KEY,
                total_votes INT DEFAULT 0,
                correct_votes INT DEFAULT 0,
                win_rate DECIMAL(5,2) DEFAULT 0,
                total_xp INT DEFAULT 0,
                total_tokens INT DEFAULT 0,
                avg_confidence DECIMAL(5,2) DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS deepseek_strategies (
                id SERIAL PRIMARY KEY,
                strategy_name VARCHAR(100),
                description TEXT,
                rules JSONB,
                applied_to VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT TRUE
            )
            """
        ]
        
        for query in queries:
            self.cursor.execute(query)
        self.conn.commit()
    
    def save_agent_result(self, data: Dict):
        """Save agent performance data"""
        query = """
            INSERT INTO agent_performance 
            (agent_name, symbol, vote, actual_result, confidence, xp, tokens, correct, reasoning, deepseek_feedback, trade_pnl)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(query, (
            data['agent_name'],
            data['symbol'],
            data['vote'],
            data['actual_result'],
            data['confidence'],
            data['xp'],
            data['tokens'],
            data['correct'],
            data.get('reasoning', ''),
            data.get('deepseek_feedback', ''),
            data.get('trade_pnl', 0)
        ))
        self.conn.commit()
    
    def update_ranking(self, agent_name: str, result: Dict):
        """Update agent ranking"""
        query = """
            INSERT INTO agent_rankings (agent_name, total_votes, correct_votes, win_rate, total_xp, total_tokens, avg_confidence)
            VALUES (%s, 1, %s, %s, %s, %s, %s)
            ON CONFLICT (agent_name) DO UPDATE
            SET total_votes = agent_rankings.total_votes + 1,
                correct_votes = agent_rankings.correct_votes + %s,
                win_rate = (agent_rankings.correct_votes + %s)::DECIMAL / (agent_rankings.total_votes + 1) * 100,
                total_xp = agent_rankings.total_xp + %s,
                total_tokens = agent_rankings.total_tokens + %s,
                avg_confidence = (agent_rankings.avg_confidence * agent_rankings.total_votes + %s) / (agent_rankings.total_votes + 1),
                last_updated = CURRENT_TIMESTAMP
        """
        self.cursor.execute(query, (
            agent_name,
            1 if result['correct'] else 0,
            result['win_rate'] if result['correct'] else 0,
            result['xp'],
            result['tokens'],
            result['avg_confidence'] if result['correct'] else 0,
            1 if result['correct'] else 0,
            result['xp'],
            result['tokens'],
            result.get('confidence', 50)
        ))
        self.conn.commit()
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get agent leaderboard"""
        query = """
            SELECT * FROM agent_rankings 
            ORDER BY total_xp DESC, win_rate DESC 
            LIMIT %s
        """
        self.cursor.execute(query, (limit,))
        return self.cursor.fetchall()
    
    def get_agent_history(self, agent_name: str, limit: int = 50) -> List[Dict]:
        """Get agent voting history"""
        query = """
            SELECT * FROM agent_performance 
            WHERE agent_name = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        self.cursor.execute(query, (agent_name, limit))
        return self.cursor.fetchall()