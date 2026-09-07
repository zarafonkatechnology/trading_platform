# setup_database.py
"""
Setup PostgreSQL Database for AI Trading System
"""

import psycopg2
import os

DB_CONFIG = {
    'host': 'localhost',
    'database': 'trading_db',
    'user': 'postgres',
    'password': 'your_password_here'  # Change this!
}

def setup_database():
    """Create database and tables"""
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'trading_db'")
        if not cursor.fetchone():
            cursor.execute("CREATE DATABASE trading_db")
            print("✅ Database 'trading_db' created")
        
        # Create tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS agent_performance (
                id SERIAL PRIMARY KEY,
                agent_name VARCHAR(50),
                symbol VARCHAR(20),
                vote VARCHAR(10),
                actual_result VARCHAR(10),
                confidence INT,
                xp INT DEFAULT 0,
                tokens INT DEFAULT 0,
                correct BOOLEAN DEFAULT FALSE,
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
        
        for query in tables:
            cursor.execute(query)
        
        conn.commit()
        print("✅ All tables created successfully")
        
        # Show tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print("\n📊 Tables created:")
        for table in tables:
            print(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n⚠️ Please install PostgreSQL and update password in DB_CONFIG")

if __name__ == "__main__":
    print("=" * 50)
    print("📊 Setting up PostgreSQL Database")
    print("=" * 50)
    setup_database()