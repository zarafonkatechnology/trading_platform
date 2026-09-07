"""
Database connection and utilities for Trading Agent Platform
"""

import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import logging
import os
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.database = os.getenv('DB_NAME', 'trading_platform')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', 'lama')
        
        self.connection = None
        self.cursor_factory = psycopg2.extras.RealDictCursor

    def get_db_connection():
     import psycopg2
     import os
     from dotenv import load_dotenv
     load_dotenv()
    
     return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'trading_platform'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'lama')
    )  
    def connect(self):
        """Create database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                cursor_factory=self.cursor_factory
            )
            logger.info(f"Connected to database {self.database} on {self.host}:{self.port}")
            return self.connection
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_connection(self):
       """Get database connection"""
       if not self.connection or self.connection.closed:
        self.connect()
        return self.connection
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """Get a database cursor (context manager)"""
        if not self.connection or self.connection.closed:
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:  # SELECT query
                return cursor.fetchall()
            return None
    
    def execute_insert(self, query, params=None):
        """Execute insert and return ID"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                result = cursor.fetchone()
                return result['id'] if result and 'id' in result else None
            return None
    
    def execute_update(self, query, params=None):
        """Execute update and return number of affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
        return cursor.rowcount
    
    def test_connection(self):
        """Test if database is reachable"""
        try:
            result = self.execute_query("SELECT 1 as test, NOW() as time")
            if result:
                logger.info(f"Database test successful at {result[0]['time']}")
                return True
            return False
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return False
    
    def get_agents(self):
        """Get all agents from database"""
        query = "SELECT * FROM core_agents ORDER BY agent_name"
        return self.execute_query(query)
    
    def get_agent_by_name(self, agent_name):
        """Get specific agent by name"""
        query = "SELECT * FROM core_agents WHERE agent_name = %s"
        result = self.execute_query(query, (agent_name,))
        return result[0] if result else None
    
    def update_agent_trust_weight(self, agent_name, new_weight):
        """Update agent's trust weight"""
        query = """
            UPDATE core_agents 
            SET trust_weight = %s, updated_at = NOW() 
            WHERE agent_name = %s
        """
        return self.execute_update(query, (new_weight, agent_name))
    
    def add_vote_record(self, signal_id, agent_name, vote, confidence, trust_weight):
        """Record an agent's vote"""
        query = """
            INSERT INTO agent_votes_full 
            (signal_id, agent_name, vote, confidence, trust_weight_at_time, timestamp)
            VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id
        """
        return self.execute_insert(query, (signal_id, agent_name, vote, confidence, trust_weight))
    
    def add_telegram_signal(self, signal_data):
        """Store incoming Telegram signal"""
        query = """
            INSERT INTO telegram_signals 
            (message_id, chat_id, asset_type, current_price, confidence_percent, 
             signal_strength, data_source, raw_message, received_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        return self.execute_insert(query, (
            signal_data.get('message_id'),
            signal_data.get('chat_id'),
            signal_data.get('asset_type'),
            signal_data.get('current_price'),
            signal_data.get('confidence_percent'),
            signal_data.get('signal_strength'),
            signal_data.get('data_source'),
            signal_data.get('raw_message'),
            signal_data.get('received_at', datetime.now())
        ))
    
    def add_group_vote_result(self, signal_id, vote_counts, percentages, final_decision):
        """Store group voting result"""
        query = """
            INSERT INTO group_votes 
            (signal_id, buy_votes, sell_votes, hold_votes, 
             buy_percent, sell_percent, hold_percent, final_decision, decision_confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        return self.execute_insert(query, (
            signal_id,
            vote_counts.get('buy', 0),
            vote_counts.get('sell', 0),
            vote_counts.get('hold', 0),
            percentages.get('buy', 0),
            percentages.get('sell', 0),
            percentages.get('hold', 0),
            final_decision.get('decision'),
            final_decision.get('confidence', 0)
        ))

# Create singleton instance
db_manager = DatabaseManager()

def get_db():
    """Get database connection"""
    if not db_manager.connection or db_manager.connection.closed:
        db_manager.connect()
    return db_manager.connection
