#!/usr/bin/env python3
"""
Extract expert decisions from historical trades and market conditions.
Output: CSV file with features + expert action (BUY/SELL/HOLD)
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'trading_platform',
    'user': 'postgres',
    'password': 'lama'
}

def fetch_trades_with_context():
    """Join trades with market snapshots and S/R analysis."""
    query = """
    SELECT 
        t.id,
        t.symbol,
        t.action AS trade_action,
        t.entry_price,
        t.exit_price,
        t.pnl,
        t.confidence AS trade_confidence,
        s.rsi,
        s.volume,
        s.volume_ratio,
        s.volatility,
        s.supply_distance,
        s.demand_distance,
        s.manipulation_score,
        s.zone_strength,
        s.touches,
        s.hidden_funds_estimate,
        t.created_at
    FROM trades t
    LEFT JOIN market_snapshots s ON t.signal_id = s.signal_id
    WHERE t.pnl IS NOT NULL
    ORDER BY t.created_at DESC
    """
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def define_expert_action(row):
    """
    Define expert action based on trade outcome.
    If trade was profitable -> action = original trade_action (BUY/SELL)
    If trade lost -> action = opposite of trade_action (or HOLD if uncertain)
    """
    if row['pnl'] > 0:
        return row['trade_action']
    elif row['pnl'] < 0:
        # For losing trade, expert would have done opposite
        if row['trade_action'] == 'BUY':
            return 'SELL'
        elif row['trade_action'] == 'SELL':
            return 'BUY'
        else:
            return 'HOLD'
    else:
        return 'HOLD'

def prepare_features(df):
    """Select and normalize features for training."""
    feature_cols = [
        'rsi', 'volume_ratio', 'volatility',
        'supply_distance', 'demand_distance', 'manipulation_score',
        'zone_strength', 'touches', 'hidden_funds_estimate'
    ]
    # Normalize numeric columns
    for col in feature_cols:
        if col in df.columns:
            # Fill missing with median
            df[col] = df[col].fillna(df[col].median())
            # Simple scaling (will be standardized later)
            df[col] = df[col] / (df[col].abs().max() + 1e-8)
    return df[feature_cols]

def main():
    print("Fetching trade data...")
    df = fetch_trades_with_context()
    print(f"Found {len(df)} trades with market context.")
    
    if df.empty:
        print("No trade data available. Run some trades first or insert sample data.")
        return
    
    # Create expert action column
    df['expert_action'] = df.apply(define_expert_action, axis=1)
    
    # Prepare features
    X = prepare_features(df)
    y = df['expert_action']
    
    # Combine into a single DataFrame for export
    output_df = pd.DataFrame(X)
    output_df['expert_action'] = y
    output_df['trade_pnl'] = df['pnl']
    output_df['trade_confidence'] = df['trade_confidence']
    
    # Save to CSV
    output_file = 'expert_dataset.csv'
    output_df.to_csv(output_file, index=False)
    print(f"✅ Saved {len(output_df)} expert examples to {output_file}")
    print("\nSample of expert data:")
    print(output_df.head())
    
    # Summary statistics
    print("\nAction distribution:")
    print(output_df['expert_action'].value_counts())
    
if __name__ == '__main__':
    main()
