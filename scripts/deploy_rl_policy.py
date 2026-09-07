#!/usr/bin/env python3
"""
Deploy fine‑tuned RL policy for real‑time trading decisions.
Loads the model, preprocesses market data, and returns BUY/SELL/HOLD.
"""

import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import os
import json
from datetime import datetime

# ============================================================
# 1. Load the fine‑tuned policy
# ============================================================
def load_policy(model_path='finetuned_policy.pt'):
    """Load fine‑tuned policy network and preprocessor."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model {model_path} not found. Run a2c_finetune.py first.")
    
    checkpoint = torch.load(model_path)
    
    # Recreate policy network
    from ha3c_pretrain import PolicyNetwork  # or define it here
    input_dim = len(checkpoint['feature_cols'])
    output_dim = len(checkpoint['action_map'])
    policy = PolicyNetwork(input_dim=input_dim, output_dim=output_dim)
    policy.load_state_dict(checkpoint['policy_state_dict'])
    policy.eval()
    
    scaler = checkpoint['scaler']
    feature_cols = checkpoint['feature_cols']
    action_map = checkpoint['action_map']
    inv_action_map = {v: k for k, v in action_map.items()}
    
    print(f"✅ Loaded fine‑tuned policy (features: {feature_cols})")
    return policy, scaler, feature_cols, inv_action_map

# ============================================================
# 2. Feature extractor from live market data
# ============================================================
def extract_features(market_data, feature_cols):
    """
    Convert live market data to feature vector expected by the policy.
    market_data: dict with keys: price, volume_ratio, volatility,
                 supply_distance, demand_distance, manipulation_score,
                 zone_strength, touches, hidden_funds_estimate
    """
    features = []
    for col in feature_cols:
        if col not in market_data:
            raise KeyError(f"Missing feature: {col}")
        features.append(market_data[col])
    return np.array(features, dtype=np.float32)

# ============================================================
# 3. Real‑time decision function
# ============================================================
def get_trade_signal(policy, scaler, feature_cols, inv_action_map, market_data):
    """Return trade action (BUY/SELL/HOLD) and confidence."""
    raw_features = extract_features(market_data, feature_cols)
    # Normalize using the same scaler from training
    scaled_features = scaler.transform([raw_features])[0]
    input_tensor = torch.tensor(scaled_features, dtype=torch.float32).unsqueeze(0)
    
    with torch.no_grad():
        logits = policy(input_tensor)
        probs = torch.softmax(logits, dim=-1).squeeze().numpy()
        action_idx = torch.argmax(logits, dim=1).item()
    
    action = inv_action_map[action_idx]
    confidence = probs[action_idx] * 100  # percentage
    return action, confidence, probs

# ============================================================
# 4. Integration with your existing agent (e.g., Agent_W or consensus)
# ============================================================
class RLPolicyAgent:
    """Wrapper to replace rule‑based agent voting."""
    def __init__(self, name="RL_Agent"):
        self.name = name
        self.policy, self.scaler, self.feature_cols, self.inv_action_map = load_policy()
    
    def analyze(self, signal_data):
        """
        signal_data: dict containing all required features.
        Returns a vote dict compatible with your agent manager.
        """
        # Build market_data dictionary from signal_data and other agents' outputs
        market_data = {
            'price': signal_data.get('price', 1.0950),
            'volume_ratio': signal_data.get('volume_ratio', 1.0),
            'volatility': signal_data.get('volatility', 0.005),
            'supply_distance': signal_data.get('supply_distance', 0.01),
            'demand_distance': signal_data.get('demand_distance', 0.01),
            'manipulation_score': signal_data.get('manipulation_score', 0.65),
            'zone_strength': signal_data.get('zone_strength', 70),
            'touches': signal_data.get('touches', 3),
            'hidden_funds_estimate': signal_data.get('hidden_funds_estimate', 45000)
        }
        action, confidence, probs = get_trade_signal(
            self.policy, self.scaler, self.feature_cols, self.inv_action_map, market_data
        )
        return {
            'agent': self.name,
            'vote': action,
            'confidence': confidence,
            'reasoning': f"RL policy decision (probs: BUY={probs[0]:.2f}, SELL={probs[1]:.2f}, HOLD={probs[2]:.2f})"
        }

# ============================================================
# 5. Example usage (CLI test)
# ============================================================
if __name__ == '__main__':
    # Example market data (simulate from your system)
    test_data = {
        'price': 1.0950,
        'volume_ratio': 1.2,
        'volatility': 0.008,
        'supply_distance': 0.003,
        'demand_distance': 0.005,
        'manipulation_score': 0.72,
        'zone_strength': 78,
        'touches': 3,
        'hidden_funds_estimate': 52000
    }
    
    policy, scaler, feature_cols, inv_action_map = load_policy()
    action, confidence, probs = get_trade_signal(
        policy, scaler, feature_cols, inv_action_map, test_data
    )
    print(f"📊 Trade Signal: {action} (confidence: {confidence:.1f}%)")
    print(f"   Probabilities: BUY={probs[0]:.2f}, SELL={probs[1]:.2f}, HOLD={probs[2]:.2f}")
