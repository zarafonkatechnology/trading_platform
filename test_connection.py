import psycopg2
import psycopg2.extras

# Try to connect and show current database
try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="trading_platform",
        user="postgres",
        password="lama"
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database()")
    db_name = cur.fetchone()[0]
    print(f"✅ Connected to database: {db_name}")
    
    cur.execute("SELECT COUNT(*) FROM core_agents")
    count = cur.fetchone()[0]
    print(f"✅ Found {count} agents in core_agents")
    
    conn.close()
except Exception as e:
    print(f"❌ Error: {e}")
