# insert_test_price.py
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="trading_platform",
        user="postgres",
        password="lama"
    )
    cur = conn.cursor()
    
    # Insert a test gold price
    cur.execute("""
        INSERT INTO price_cache (symbol, display_name, bid, ask, mid, source, updated_at)
        VALUES ('GOLD', 'GOLD', 2035.50, 2036.00, 2035.75, 'MANUAL', NOW())
        ON CONFLICT (symbol) DO UPDATE SET
            bid = EXCLUDED.bid,
            ask = EXCLUDED.ask,
            mid = EXCLUDED.mid,
            source = 'MANUAL',
            updated_at = NOW()
    """)
    
    conn.commit()
    print("✅ Inserted gold price: $2035.75")
    
    # Verify
    cur.execute("SELECT * FROM price_cache")
    rows = cur.fetchall()
    print(f"\n📊 Price cache now has {len(rows)} records:")
    for row in rows:
        print(f"   {row}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
