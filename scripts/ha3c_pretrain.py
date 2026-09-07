#!/usr/bin/env python3
"""
HA3C Pretraining: Learn from expert dataset (supervised learning)
Handles small datasets gracefully.
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import os
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# 1. Load expert dataset (CSV)
# ============================================================
def load_dataset(csv_path='expert_dataset.csv'):
    """Load expert dataset and prepare features/targets."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset {csv_path} not found. Run build_expert_dataset.py first.")
    
    df = pd.read_csv(csv_path)
    print(f"📊 Loaded {len(df)} expert examples from {csv_path}")
    
    # Define feature columns
    feature_cols = [
        'rsi', 'volume_ratio', 'volatility',
        'supply_distance', 'demand_distance', 'manipulation_score',
        'zone_strength', 'touches', 'hidden_funds_estimate'
    ]
    
    # Map actions: BUY=0, SELL=1, HOLD=2
    action_map = {'BUY': 0, 'SELL': 1, 'HOLD': 2}
    df['action_code'] = df['expert_action'].map(action_map)
    
    # Drop rows with missing values
    df = df.dropna(subset=feature_cols + ['action_code'])
    
    X = df[feature_cols].values
    y = df['action_code'].values
    
    print(f"✅ Action distribution: {dict(zip(*np.unique(y, return_counts=True)))}")
    return X, y, feature_cols, action_map, df

# ============================================================
# 2. Define Policy Network
# ============================================================
class PolicyNetwork(nn.Module):
    def __init__(self, input_dim=9, hidden_dim=64, output_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim)
        )
    
    def forward(self, x):
        return self.net(x)

# ============================================================
# 3. Training function (handles small datasets)
# ============================================================
def train_pretrained_model(X, y, feature_cols, action_map, 
                           test_size=0.2, batch_size=4, epochs=100, lr=0.001):
    
    n_samples = len(X)
    print(f"\n📈 Training on {n_samples} samples")
    
    # For very small datasets, use a simple validation split without stratification
    if n_samples < 10:
        print("⚠️ Small dataset detected. Using simple random split (no stratification).")
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=min(0.3, 2/n_samples), random_state=42
        )
    else:
        try:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
        except ValueError:
            print("⚠️ Stratification failed. Using simple random split.")
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
    
    # Normalize features
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)
    
    print(f"   Training samples: {len(X_train)}")
    print(f"   Validation samples: {len(X_val)}")
    
    # Convert to tensors
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_val_t = torch.tensor(X_val, dtype=torch.float32)
    y_val_t = torch.tensor(y_val, dtype=torch.long)
    
    # Model, loss, optimizer
    model = PolicyNetwork(input_dim=len(feature_cols))
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    print("\n🚀 Starting HA3C pretraining (supervised learning)...")
    
    best_val_acc = 0.0
    for epoch in range(1, epochs + 1):
        model.train()
        perm = torch.randperm(len(X_train_t))
        epoch_loss = 0.0
        correct = 0
        n_batches = 0
        
        for i in range(0, len(X_train_t), batch_size):
            idx = perm[i:i+batch_size]
            xb, yb = X_train_t[idx], y_train_t[idx]
            
            optimizer.zero_grad()
            logits = model(xb)
            loss = criterion(logits, yb)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            correct += (logits.argmax(1) == yb).sum().item()
            n_batches += 1
        
        train_acc = correct / len(X_train_t) * 100 if len(X_train_t) > 0 else 0
        
        # Validation
        model.eval()
        with torch.no_grad():
            if len(X_val_t) > 0:
                val_logits = model(X_val_t)
                val_loss = criterion(val_logits, y_val_t).item()
                val_acc = (val_logits.argmax(1) == y_val_t).float().mean().item() * 100
            else:
                val_acc = 0
        
        if epoch % 20 == 0 or epoch == epochs:
            print(f"Epoch {epoch:3d} | Loss: {epoch_loss/n_batches:.4f} | Train Acc: {train_acc:.1f}% | Val Acc: {val_acc:.1f}%")
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save({
                'model_state_dict': model.state_dict(),
                'scaler': scaler,
                'feature_cols': feature_cols,
                'action_map': action_map,
                'val_acc': val_acc
            }, 'pretrained_policy_best.pt')
    
    # Save final model
    torch.save({
        'model_state_dict': model.state_dict(),
        'scaler': scaler,
        'feature_cols': feature_cols,
        'action_map': action_map,
        'val_acc': val_acc
    }, 'pretrained_policy.pt')
    
    print(f"\n✅ Pretrained policy saved to 'pretrained_policy.pt' (best val acc: {best_val_acc:.1f}%)")
    return model, scaler

# ============================================================
# 4. Main execution
# ============================================================
if __name__ == '__main__':
    # Load dataset
    X, y, feature_cols, action_map, df = load_dataset('expert_dataset.csv')
    
    if len(X) < 2:
        print("\n❌ Not enough expert data. Need at least 2 samples.")
        print("   Run more trades or add sample data first.")
        exit(1)
    
    # Train pretrained model
    model, scaler = train_pretrained_model(X, y, feature_cols, action_map)
    
    # Quick test on a random sample
    if len(X) > 0:
        sample_idx = np.random.randint(0, len(X))
        sample = X[sample_idx:sample_idx+1]
        sample_scaled = scaler.transform(sample)
        sample_t = torch.tensor(sample_scaled, dtype=torch.float32)
        with torch.no_grad():
            logits = model(sample_t)
            pred = logits.argmax().item()
        inv_map = {v: k for k, v in action_map.items()}
        print(f"\n📊 Example prediction: {inv_map[pred]} (true action was {inv_map[y[sample_idx]]})")
