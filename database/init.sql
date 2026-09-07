-- =====================================================
-- TRADING AGENT PLATFORM - DATABASE SCHEMA
-- Simplified version for initial setup
-- =====================================================

-- Drop tables if they exist (in reverse order)
DROP TABLE IF EXISTS signed_actions CASCADE;
DROP TABLE IF EXISTS agent_sessions CASCADE;
DROP TABLE IF EXISTS security_events CASCADE;
DROP TABLE IF EXISTS agent_identities CASCADE;
DROP TABLE IF EXISTS collaboration_metrics CASCADE;
DROP TABLE IF EXISTS zero_error_milestones CASCADE;
DROP TABLE IF EXISTS ml_training_cycles CASCADE;
DROP TABLE IF EXISTS rl_experience_buffer CASCADE;
DROP TABLE IF EXISTS rl_episodes CASCADE;
DROP TABLE IF EXISTS smi_features CASCADE;
DROP TABLE IF EXISTS smi_5min_candles CASCADE;
DROP TABLE IF EXISTS gatekeeper_full_audit CASCADE;
DROP TABLE IF EXISTS agent_learning_progress CASCADE;
DROP TABLE IF EXISTS agent_errors CASCADE;
DROP TABLE IF EXISTS supervisor_decisions_full CASCADE;
DROP TABLE IF EXISTS supervisor_vote_records CASCADE;
DROP TABLE IF EXISTS telegram_metrics CASCADE;
DROP TABLE IF EXISTS telegram_signals CASCADE;
DROP TABLE IF EXISTS execution_decisions CASCADE;
DROP TABLE IF EXISTS group_votes CASCADE;
DROP TABLE IF EXISTS agent_votes_full CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS knowledge_exchange CASCADE;
DROP TABLE IF EXISTS agent_rewards CASCADE;
DROP TABLE IF EXISTS achievements_catalog CASCADE;
DROP TABLE IF EXISTS agent_learning_topics CASCADE;
DROP TABLE IF EXISTS agent_conversations CASCADE;
DROP TABLE IF EXISTS broadcast_queue CASCADE;
DROP TABLE IF EXISTS platform_savepoints CASCADE;
DROP TABLE IF EXISTS core_agents CASCADE;

-- =====================================================
-- CORE AGENTS TABLE
-- =====================================================
CREATE TABLE core_agents (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) UNIQUE NOT NULL,
    agent_type VARCHAR(30),
    specialization VARCHAR(50),
    xp_points INTEGER DEFAULT 0,
    token_balance INTEGER DEFAULT 1000,
    achievements_count INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    trust_weight DECIMAL(5,4) DEFAULT 0.2000,
    total_votes INTEGER DEFAULT 0,
    correct_votes INTEGER DEFAULT 0,
    vote_accuracy DECIMAL(5,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_enrolled BOOLEAN DEFAULT FALSE,
    enrollment_date TIMESTAMP,
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- AGENT IDENTITIES & SECURITY
-- =====================================================
CREATE TABLE agent_identities (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) UNIQUE NOT NULL REFERENCES core_agents(agent_name),
    electronic_fingerprint VARCHAR(128) UNIQUE NOT NULL,
    fingerprint_algorithm VARCHAR(20) DEFAULT 'SHA3-256',
    public_key TEXT NOT NULL,
    private_key_encrypted TEXT NOT NULL,
    certificate_serial VARCHAR(64) UNIQUE,
    certificate_issued_at TIMESTAMP DEFAULT NOW(),
    certificate_expires_at TIMESTAMP,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_sessions (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) REFERENCES agent_identities(agent_name),
    session_token VARCHAR(256) UNIQUE NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    last_activity TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    terminated_reason TEXT
);

CREATE TABLE signed_actions (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20),
    action_type VARCHAR(50),
    action_id INTEGER,
    action_data TEXT,
    action_hash VARCHAR(128),
    agent_signature TEXT,
    verification_result BOOLEAN,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE security_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    agent_name VARCHAR(20),
    error_message TEXT,
    severity INTEGER DEFAULT 5,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- TELEGRAM SIGNALS
-- =====================================================
CREATE TABLE telegram_signals (
    id SERIAL PRIMARY KEY,
    message_id BIGINT UNIQUE,
    chat_id BIGINT,
    asset_type VARCHAR(20),
    current_price DECIMAL(12,4),
    confidence_percent DECIMAL(5,2),
    signal_strength VARCHAR(20),
    data_source VARCHAR(20),
    raw_message TEXT,
    received_at TIMESTAMP DEFAULT NOW(),
    total_processing_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE telegram_metrics (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    total_messages_received INTEGER DEFAULT 0,
    strong_signals INTEGER DEFAULT 0,
    weak_signals INTEGER DEFAULT 0,
    avg_confidence DECIMAL(5,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- VOTING SYSTEM
-- =====================================================
CREATE TABLE agent_votes_full (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    agent_name VARCHAR(20) REFERENCES core_agents(agent_name),
    vote VARCHAR(4),
    confidence DECIMAL(5,2),
    trust_weight_at_time DECIMAL(5,4),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE group_votes (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    buy_votes INTEGER,
    sell_votes INTEGER,
    hold_votes INTEGER,
    buy_percent DECIMAL(5,2),
    sell_percent DECIMAL(5,2),
    hold_percent DECIMAL(5,2),
    final_decision VARCHAR(4),
    decision_confidence DECIMAL(5,2),
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE supervisor_vote_records (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    agent_name VARCHAR(20) REFERENCES core_agents(agent_name),
    vote_cast VARCHAR(4),
    confidence DECIMAL(5,2),
    was_correct BOOLEAN,
    error_type VARCHAR(50),
    xp_gained INTEGER DEFAULT 0,
    xp_lost INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE supervisor_decisions_full (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    total_buy_votes INTEGER,
    total_sell_votes INTEGER,
    total_hold_votes INTEGER,
    buy_percentage DECIMAL(5,2),
    sell_percentage DECIMAL(5,2),
    hold_percentage DECIMAL(5,2),
    final_decision VARCHAR(4),
    decision_confidence DECIMAL(5,2),
    consensus_achieved BOOLEAN,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- GATEKEEPER
-- =====================================================
CREATE TABLE gatekeeper_full_audit (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    agent_name VARCHAR(20),
    pillar1_identity_passed BOOLEAN,
    pillar2_logic_passed BOOLEAN,
    pillar3_resource_passed BOOLEAN,
    gate_status VARCHAR(30),
    block_reason TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- ERROR CORRECTION
-- =====================================================
CREATE TABLE agent_errors (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) REFERENCES core_agents(agent_name),
    signal_id INTEGER REFERENCES telegram_signals(id),
    error_category VARCHAR(50),
    error_description TEXT,
    root_cause TEXT,
    severity INTEGER DEFAULT 5,
    is_fixed BOOLEAN DEFAULT FALSE,
    fixed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_learning_progress (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20) REFERENCES core_agents(agent_name),
    learning_date DATE DEFAULT CURRENT_DATE,
    topics_learned_today TEXT[] DEFAULT '{}',
    lessons_received INTEGER DEFAULT 0,
    xp_gained_today INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- KNOWLEDGE EXCHANGE
-- =====================================================
CREATE TABLE knowledge_exchange (
    id SERIAL PRIMARY KEY,
    from_agent VARCHAR(20),
    to_agent VARCHAR(20),
    knowledge_type VARCHAR(50),
    topic VARCHAR(200),
    content TEXT,
    xp_reward INTEGER DEFAULT 10,
    token_reward INTEGER DEFAULT 5,
    is_broadcast BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_conversations (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20),
    conversation_with VARCHAR(20),
    message TEXT,
    message_type VARCHAR(20),
    xp_earned INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE agent_learning_topics (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20),
    topic_name VARCHAR(100),
    content TEXT,
    source_agent VARCHAR(20),
    is_learned BOOLEAN DEFAULT FALSE,
    learned_at TIMESTAMP,
    xp_gained INTEGER DEFAULT 0
);

CREATE TABLE broadcast_queue (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(200),
    content TEXT,
    broadcast_by VARCHAR(20),
    total_agents INTEGER DEFAULT 5,
    delivered_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- REWARDS & ACHIEVEMENTS
-- =====================================================
CREATE TABLE agent_rewards (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20),
    reward_type VARCHAR(30),
    reward_name VARCHAR(100),
    reward_value INTEGER,
    unlocked_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE achievements_catalog (
    id SERIAL PRIMARY KEY,
    achievement_name VARCHAR(100),
    description TEXT,
    required_xp INTEGER,
    reward_xp INTEGER,
    reward_tokens INTEGER
);

-- Insert achievements
INSERT INTO achievements_catalog (achievement_name, description, required_xp, reward_xp, reward_tokens) VALUES
('Novice Trader', 'Complete first 10 trades', 0, 50, 100),
('Seasoned Pro', 'Reach 1,000 XP', 1000, 200, 500),
('Master Trader', 'Reach 5,000 XP', 5000, 500, 1000);

-- =====================================================
-- MARKET DATA
-- =====================================================
CREATE TABLE smi_5min_candles (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume INTEGER,
    UNIQUE(timestamp)
);

CREATE TABLE smi_features (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    z_score_20 DECIMAL(8,4),
    z_score_50 DECIMAL(8,4),
    rsi_14 DECIMAL(8,4),
    rsi_slope_5 DECIMAL(8,4),
    trend_strength DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- ML TRAINING
-- =====================================================
CREATE TABLE rl_experience_buffer (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(20),
    timestamp TIMESTAMPTZ NOT NULL,
    state_features JSONB NOT NULL,
    action VARCHAR(4),
    reward DECIMAL(10,4),
    xp_change INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ml_training_cycles (
    id SERIAL PRIMARY KEY,
    cycle_number INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    pre_training_accuracy DECIMAL(5,2),
    post_training_accuracy DECIMAL(5,2),
    agents_trained TEXT[],
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- COLLABORATION METRICS
-- =====================================================
CREATE TABLE collaboration_metrics (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES telegram_signals(id),
    consensus_reached BOOLEAN,
    consensus_percentage DECIMAL(5,2),
    teamwork_score DECIMAL(5,2),
    zero_error_contribution BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE zero_error_milestones (
    id SERIAL PRIMARY KEY,
    milestone_name VARCHAR(100),
    achieved_at TIMESTAMP,
    consecutive_correct_trades INTEGER,
    achieving_agents TEXT[],
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- PLATFORM SAVEPOINTS
-- =====================================================
CREATE TABLE platform_savepoints (
    id SERIAL PRIMARY KEY,
    checkpoint_time TIMESTAMP DEFAULT NOW(),
    agents_snapshot JSONB,
    total_xp INTEGER,
    total_tokens INTEGER
);

-- =====================================================
-- INSERT INITIAL AGENTS
-- =====================================================
INSERT INTO core_agents (agent_name, agent_type, specialization, is_enrolled, enrollment_date, trust_weight) VALUES
('Agent_A', 'Trend Follower', 'Moving Average Crossovers', TRUE, NOW(), 0.2000),
('Agent_B', 'Mean Reversion', 'RSI & Bollinger Bands', TRUE, NOW(), 0.2000),
('Agent_C', 'Momentum', 'Price Rate of Change', TRUE, NOW(), 0.2000),
('Agent_D', 'Volatility', 'ATR & Historical Vol', TRUE, NOW(), 0.2000),
('Agent_E', 'Microstructure', 'Order Flow & Volume', TRUE, NOW(), 0.2000);

-- Verify setup
DO $$
DECLARE
    agent_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO agent_count FROM core_agents;
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'DATABASE SETUP COMPLETE!';
    RAISE NOTICE '=========================================';
    RAISE NOTICE 'Created: % agents', agent_count;
    RAISE NOTICE 'Tables created: 30+';
    RAISE NOTICE '=========================================';
END $$;

ALTER TABLE core_agents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
-- Add to your existing database
-- Run this in PostgreSQL

-- Complete signals table with all fields
ALTER TABLE signals ADD COLUMN IF NOT EXISTS signal_uuid UUID DEFAULT gen_random_uuid();
ALTER TABLE signals ADD COLUMN IF NOT EXISTS analysis_volatility DECIMAL(8,4);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS stoploss DECIMAL(12,4);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS takeprofit DECIMAL(12,4);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS support_level DECIMAL(12,4);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS resistance_level DECIMAL(12,4);
ALTER TABLE signals ADD COLUMN IF NOT EXISTS timeframe_minutes INTEGER DEFAULT 15;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS strategy_used VARCHAR(20);

-- Group votes table with percentages
CREATE TABLE IF NOT EXISTS group_votes (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    buy_votes INTEGER,
    sell_votes INTEGER,
    hold_votes INTEGER,
    buy_percent DECIMAL(5,2),
    sell_percent DECIMAL(5,2),
    hold_percent DECIMAL(5,2),
    final_decision VARCHAR(4),
    decision_confidence DECIMAL(5,2),
    key_agents TEXT[],
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Strategy framework table
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(20),
    timeframe_minutes INTEGER,
    min_confidence DECIMAL(5,2),
    required_consensus DECIMAL(5,2),
    max_slippage_bps INTEGER,
    position_size VARCHAR(10),
    stoploss_multiplier DECIMAL(4,2),
    takeprofit_multiplier DECIMAL(4,2),
    max_holding_periods INTEGER,
    is_active BOOLEAN DEFAULT TRUE
);

-- Insert strategies
INSERT INTO strategies (strategy_name, timeframe_minutes, min_confidence, required_consensus, 
    max_slippage_bps, position_size, stoploss_multiplier, takeprofit_multiplier, max_holding_periods)
VALUES 
    ('SCALPING', 5, 70, 60, 10, 'small', 1.0, 1.5, 6),
    ('DAY_TRADE', 15, 75, 60, 15, 'medium', 1.5, 2.0, 12),
    ('SWING', 60, 80, 66, 20, 'large', 2.0, 3.0, 24),
    ('POSITION', 1440, 85, 75, 30, 'full', 3.0, 5.0, 30)
ON CONFLICT DO NOTHING;

-- Execution decisions table
CREATE TABLE IF NOT EXISTS execution_decisions (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    decision_timestamp TIMESTAMP,
    execution_latency_ms INTEGER,
    strategy_used VARCHAR(50),
    entry_price DECIMAL(12,4),
    quantity INTEGER,
    total_cost DECIMAL(16,4),
    stoploss_placed DECIMAL(12,4),
    takeprofit_placed DECIMAL(12,4),
    final_buy_percent DECIMAL(5,2),
    final_sell_percent DECIMAL(5,2),
    final_hold_percent DECIMAL(5,2),
    exit_price DECIMAL(12,4),
    pnl DECIMAL(16,4),
    pnl_percent DECIMAL(8,4),
    outcome VARCHAR(10),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);