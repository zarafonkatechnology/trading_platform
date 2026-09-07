# ============================================================
# config.py - RL Trading Configuration
# ============================================================

import os
from datetime import datetime

class Config:
    # ===== ENVIRONMENT =====
    ENV_NAME = "SpreadArbitrageEnv-v1"
    TIMEFRAME = "M15"  # 15-minute candles
    
    # ===== RL PARAMETERS =====
    GAMMA = 0.9  # Discount factor (γ)
    LEARNING_RATE = 0.0003
    BATCH_SIZE = 256
    BUFFER_SIZE = 1000000
    
    # ===== TRAINING =====
    TRAINING_YEARS = 1
    TRAINING_SPLIT = 0.67  # 2 years training, 1 year validation
    TOTAL_TIMESTEPS = 100000
    N_EVALUATIONS = 50
    
    # ===== EXPLORATION =====
    EXPLORATION_FRACTION = 0.1  # ε during training
    EXPLORATION_FINAL = 0.01   # Minimum ε during training
    
    # ===== AGENTS =====
    N_AGENTS = 8  # Core agents
    AGENT_NAMES = ['R', 'Q', 'D', 'H', 'G', 'M', 'I', 'X']
    
    # ===== REWARD =====
    REWARD_TYPE = 'SHARPE'  # 'SHARPE', 'SORTINO', 'CALMAR'
    RISK_FREE_RATE = 0.02  # 2% annual
    
    # ===== HYPERLEARNING =====
    USE_HYPERLEARNING = True
    META_LEARNING_RATE = 0.001
    
    # ===== PATHS =====
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    MODELS_PATH = os.path.join(BASE_PATH, 'models')
    LOGS_PATH = os.path.join(BASE_PATH, 'logs')
    DATA_PATH = os.path.join(BASE_PATH, 'data')
    
    @classmethod
    def get_timestamp(cls):
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    @classmethod
    def print_config(cls):
        print("=" * 60)
        print("📋 RL TRADING CONFIGURATION")
        print("=" * 60)
        for key, value in cls.__dict__.items():
            if not key.startswith('_') and not callable(value):
                print(f"   {key}: {value}")
        print("=" * 60)