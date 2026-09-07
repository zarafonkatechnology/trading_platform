#!/usr/bin/env python3
"""
Database Health Check & Auto-Recovery
Run this on startup or as a cron job
"""

import subprocess
import psycopg2
import time
import sys

def check_and_fix_database():
    print("🩺 Database Health Check")
    
    # 1. Check if Docker container is running
    result = subprocess.run(["docker", "ps", "--filter", "name=trading_postgres", "--format", "{{.Status}}"], 
                           capture_output=True, text=True)
    
    if "Up" not in result.stdout:
        print("🐳 Starting PostgreSQL container...")
        subprocess.run(["docker", "start", "trading_postgres"])
        time.sleep(5)
    
    # 2. Check database connection
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="lama",
            database="trading_platform"
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM core_agents")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        print(f"✅ Database OK! {count} agents found")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"⚠️ Database issue: {e}")
        
        # Try to recreate database
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="lama",
                database="postgres"
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            # Recreate database
            cur.execute("DROP DATABASE IF EXISTS trading_platform")
            cur.execute("CREATE DATABASE trading_platform")
            
            cur.close()
            conn.close()
            
            # Recreate tables
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password="lama",
                database="trading_platform"
            )
            cur = conn.cursor()
            
            cur.execute("""
                CREATE TABLE core_agents (
                    id SERIAL PRIMARY KEY,
                    agent_name VARCHAR(50) UNIQUE NOT NULL,
                    agent_type VARCHAR(50),
                    xp_points INTEGER DEFAULT 40000,
                    token_balance INTEGER DEFAULT 1200,
                    vote_accuracy DECIMAL(5,2) DEFAULT 0
                )
            """)
            
            cur.execute("""
                INSERT INTO core_agents (agent_name, agent_type, vote_accuracy) VALUES
                    ('Agent_A', 'Trend Follower', 68.5),
                    ('Agent_B', 'Mean Reversion', 65.2),
                    ('Agent_C', 'Momentum', 71.3),
                    ('Agent_D', 'Volatility', 62.8),
                    ('Agent_E', 'Microstructure', 59.5),
                    ('Agent_F', 'Candlestick', 66.7),
                    ('Agent_G', 'Whale Tracker', 63.4),
                    ('Agent_H', 'Fibonacci', 61.2)
            """)
            
            conn.commit()
            cur.close()
            conn.close()
            
            print("✅ Database restored successfully!")
            return True
            
        except Exception as restore_error:
            print(f"❌ Could not restore database: {restore_error}")
            return False

if __name__ == "__main__":
    success = check_and_fix_database()
    sys.exit(0 if success else 1)
