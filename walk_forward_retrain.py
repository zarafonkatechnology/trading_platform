"""
Walk-Forward Retraining Pipeline
- Automatically retrains HA3C policy and A2C on weekly basis
- Uses fresh market data from feature store
- Validates performance before deployment
- Rolls back if performance degrades
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json
import os
import time
import threading
import schedule
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class RetrainConfig:
    """Configuration for walk-forward retraining"""
    # Retraining schedule
    retrain_days: int = 7              # Retrain every 7 days
    training_window_days: int = 90     # Use last 90 days for training
    validation_window_days: int = 14   # Use next 14 days for validation
    
    # Model parameters
    input_dim: int = 12
    hidden_dim: int = 128
    output_dim: int = 3
    learning_rate: float = 0.001
    
    # Training parameters
    batch_size: int = 64
    epochs_pretrain: int = 50
    epochs_a2c: int = 100
    gamma: float = 0.99
    gae_lambda: float = 0.95
    
    # Performance thresholds
    min_validation_sharpe: float = 0.3
    min_validation_win_rate: float = 0.45
    max_performance_drop: float = 0.15  # 15% max drop from previous model
    
    # Paths
    model_dir: str = "models"
    backup_dir: str = "models/backups"


class PolicyNetwork(nn.Module):
    """Policy network for HA3C"""
    
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
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


class ValueNetwork(nn.Module):
    """Value network for A2C"""
    
    def __init__(self, input_dim: int, hidden_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, x):
        return self.net(x).squeeze(-1)


class DataLoader:
    """Loads training data from feature store"""
    
    def __init__(self, feature_store_path: str = "feature_store.db"):
        self.feature_store_path = feature_store_path
        self.conn = None
    
    def get_training_data(self, end_date: datetime, 
                          training_days: int = 90,
                          validation_days: int = 14) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Get training and validation datasets"""
        
        train_start = end_date - timedelta(days=training_days)
        train_end = end_date
        
        val_start = end_date
        val_end = end_date + timedelta(days=validation_days)
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.feature_store_path)
            
            # Load training data
            train_query = f"""
                SELECT * FROM features 
                WHERE timestamp BETWEEN '{train_start.isoformat()}' AND '{train_end.isoformat()}'
                AND actual_outcome IS NOT NULL
                ORDER BY timestamp
            """
            train_df = pd.read_sql_query(train_query, conn)
            
            # Load validation data
            val_query = f"""
                SELECT * FROM features 
                WHERE timestamp BETWEEN '{val_start.isoformat()}' AND '{val_end.isoformat()}'
                AND actual_outcome IS NOT NULL
                ORDER BY timestamp
            """
            val_df = pd.read_sql_query(val_query, conn)
            
            conn.close()
            
            logger.info(f"Loaded {len(train_df)} training samples, {len(val_df)} validation samples")
            return train_df, val_df
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            # Return simulated data for testing
            return self._generate_simulated_data(training_days * 24), self._generate_simulated_data(validation_days * 24)
    
    def _generate_simulated_data(self, n_samples: int) -> pd.DataFrame:
        """Generate simulated data for testing"""
        data = []
        for i in range(n_samples):
            data.append({
                'rsi': 50 + np.random.normal(0, 15),
                'volume_ratio': np.random.uniform(0.5, 2.0),
                'volatility': np.random.uniform(0.005, 0.02),
                'supply_distance': np.random.uniform(0.001, 0.01),
                'demand_distance': np.random.uniform(0.001, 0.01),
                'manipulation_score': np.random.uniform(0, 1),
                'zone_strength': np.random.uniform(30, 90),
                'touches': np.random.randint(1, 6),
                'hidden_funds_estimate': np.random.randint(10000, 100000),
                'consensus_action': np.random.choice(['BUY', 'SELL', 'HOLD']),
                'actual_outcome': np.random.uniform(-0.02, 0.02),
                'reward': np.random.uniform(-10, 10)
            })
        return pd.DataFrame(data)


class HA3CPretrainer:
    """HA3C pretraining from expert data"""
    
    def __init__(self, config: RetrainConfig):
        self.config = config
        self.policy = PolicyNetwork(config.input_dim, config.hidden_dim, config.output_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=config.learning_rate)
        self.criterion = nn.CrossEntropyLoss()
        self.scaler = None
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels from DataFrame"""
        feature_cols = ['rsi', 'volume_ratio', 'volatility', 'supply_distance',
                       'demand_distance', 'manipulation_score', 'zone_strength',
                       'touches', 'hidden_funds_estimate']
        
        # Add synthetic features if missing
        for col in feature_cols:
            if col not in df.columns:
                df[col] = np.random.uniform(0, 1, len(df))
        
        X = df[feature_cols].values
        
        # Normalize features
        from sklearn.preprocessing import StandardScaler
        self.scaler = StandardScaler()
        X = self.scaler.fit_transform(X)
        
        # Map actions to integers
        action_map = {'BUY': 0, 'SELL': 1, 'HOLD': 2}
        y = df['consensus_action'].map(action_map).fillna(2).values
        
        return X, y
    
    def train(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> Dict:
        """Train policy network on expert data"""
        logger.info("Starting HA3C pretraining...")
        
        X_train, y_train = self.prepare_features(train_df)
        X_val, y_val = self.prepare_features(val_df)
        
        X_train_t = torch.tensor(X_train, dtype=torch.float32)
        y_train_t = torch.tensor(y_train, dtype=torch.long)
        X_val_t = torch.tensor(X_val, dtype=torch.float32)
        y_val_t = torch.tensor(y_val, dtype=torch.long)
        
        best_val_acc = 0
        history = []
        
        for epoch in range(self.config.epochs_pretrain):
            self.policy.train()
            permutation = torch.randperm(len(X_train_t))
            epoch_loss = 0
            
            for i in range(0, len(X_train_t), self.config.batch_size):
                idx = permutation[i:i+self.config.batch_size]
                xb, yb = X_train_t[idx], y_train_t[idx]
                
                self.optimizer.zero_grad()
                logits = self.policy(xb)
                loss = self.criterion(logits, yb)
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item()
            
            # Validation
            self.policy.eval()
            with torch.no_grad():
                val_logits = self.policy(X_val_t)
                val_acc = (val_logits.argmax(1) == y_val_t).float().mean().item()
                val_loss = self.criterion(val_logits, y_val_t).item()
            
            history.append({'epoch': epoch, 'val_acc': val_acc, 'val_loss': val_loss})
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                self._save_checkpoint('best_pretrain.pt')
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}: val_acc={val_acc:.3f}, val_loss={val_loss:.4f}")
        
        self._save_checkpoint('final_pretrain.pt')
        
        logger.info(f"HA3C pretraining complete. Best val_acc: {best_val_acc:.3f}")
        
        return {
            'best_accuracy': best_val_acc,
            'history': history,
            'scaler': self.scaler
        }
    
    def _save_checkpoint(self, filename: str):
        """Save checkpoint"""
        os.makedirs(self.config.model_dir, exist_ok=True)
        path = os.path.join(self.config.model_dir, filename)
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'scaler': self.scaler,
            'config': self.config
        }, path)


class A2CFineTuner:
    """A2C fine-tuning after HA3C pretraining"""
    
    def __init__(self, config: RetrainConfig, pretrained_policy: PolicyNetwork):
        self.config = config
        self.policy = pretrained_policy
        self.value_net = ValueNetwork(config.input_dim, config.hidden_dim)
        self.policy_optimizer = optim.Adam(self.policy.parameters(), lr=config.learning_rate)
        self.value_optimizer = optim.Adam(self.value_net.parameters(), lr=config.learning_rate)
    
    def compute_gae(self, rewards: List[float], values: List[float], 
                    dones: List[bool], next_value: float) -> List[float]:
        """Compute Generalized Advantage Estimation"""
        advantages = []
        gae = 0
        for t in reversed(range(len(rewards))):
            if dones[t]:
                delta = rewards[t] - values[t]
                gae = delta
            else:
                delta = rewards[t] + self.config.gamma * next_value - values[t]
                gae = delta + self.config.gamma * self.config.gae_lambda * gae
            advantages.insert(0, gae)
            next_value = values[t]
        return advantages
    
    def train_episode(self, env, max_steps: int = 100) -> Tuple[float, float]:
        """Train on one episode"""
        states = []
        actions = []
        rewards = []
        dones = []
        values = []
        
        state = env.reset()
        
        for step in range(max_steps):
            state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            
            # Get action from policy
            with torch.no_grad():
                logits = self.policy(state_t)
                probs = torch.softmax(logits, dim=-1)
                action = torch.multinomial(probs, 1).item()
                value = self.value_net(state_t).item()
            
            next_state, reward, done = env.step(action)
            
            states.append(state)
            actions.append(action)
            rewards.append(reward)
            dones.append(done)
            values.append(value)
            
            state = next_state
            if done:
                break
        
        # Compute returns and advantages
        with torch.no_grad():
            next_state_t = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
            next_value = self.value_net(next_state_t).item()
        
        advantages = self.compute_gae(rewards, values, dones, next_value)
        returns = [adv + val for adv, val in zip(advantages, values)]
        
        # Convert to tensors
        states_t = torch.tensor(np.array(states), dtype=torch.float32)
        actions_t = torch.tensor(actions, dtype=torch.long)
        returns_t = torch.tensor(returns, dtype=torch.float32)
        advantages_t = torch.tensor(advantages, dtype=torch.float32)
        
        # Update value network
        values_t = self.value_net(states_t)
        value_loss = nn.MSELoss()(values_t, returns_t)
        
        self.value_optimizer.zero_grad()
        value_loss.backward()
        self.value_optimizer.step()
        
        # Update policy network
        logits = self.policy(states_t)
        log_probs = torch.log_softmax(logits, dim=-1)
        selected_log_probs = log_probs.gather(1, actions_t.unsqueeze(1)).squeeze()
        policy_loss = -(selected_log_probs * advantages_t.detach()).mean()
        
        self.policy_optimizer.zero_grad()
        policy_loss.backward()
        self.policy_optimizer.step()
        
        total_reward = sum(rewards)
        
        return total_reward, value_loss.item() + policy_loss.item()
    
    def train(self, env, episodes: int) -> Dict:
        """Run A2C training"""
        logger.info(f"Starting A2C fine-tuning for {episodes} episodes...")
        
        rewards_history = []
        losses = []
        
        for episode in range(episodes):
            total_reward, loss = self.train_episode(env)
            rewards_history.append(total_reward)
            losses.append(loss)
            
            if (episode + 1) % 20 == 0:
                avg_reward = np.mean(rewards_history[-20:])
                logger.info(f"Episode {episode+1}: avg_reward={avg_reward:.2f}, loss={loss:.4f}")
        
        self._save_checkpoint('final_a2c.pt')
        
        return {
            'final_avg_reward': np.mean(rewards_history[-100:]),
            'rewards_history': rewards_history,
            'losses': losses
        }
    
    def _save_checkpoint(self, filename: str):
        """Save checkpoint"""
        os.makedirs(self.config.model_dir, exist_ok=True)
        path = os.path.join(self.config.model_dir, filename)
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'value_state_dict': self.value_net.state_dict(),
            'config': self.config
        }, path)


class TradingEnvironment:
    """Simple trading environment for A2C training"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.current_step = 0
        self.position = 0
        self.entry_price = 0
    
    def reset(self) -> np.ndarray:
        """Reset environment"""
        self.current_step = 0
        self.position = 0
        self.entry_price = 0
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state vector"""
        if self.current_step >= len(self.data):
            return np.zeros(12)
        
        row = self.data.iloc[self.current_step]
        return np.array([
            row.get('rsi', 50) / 100,
            min(1.0, row.get('volume_ratio', 1.0) / 2),
            min(1.0, row.get('volatility', 0.01) * 100),
            min(0.05, row.get('supply_distance', 0.005)) * 200,
            min(0.05, row.get('demand_distance', 0.005)) * 200,
            row.get('manipulation_score', 0.5),
            row.get('zone_strength', 50) / 100,
            min(1.0, row.get('touches', 3) / 10),
            min(1.0, row.get('hidden_funds_estimate', 50000) / 100000),
            self.position,
            0.5,  # placeholder
            0.5   # placeholder
        ], dtype=np.float32)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """Take action and return next state, reward, done"""
        current_price = self.data.iloc[self.current_step].get('price', 100)
        next_price = self.data.iloc[min(self.current_step + 1, len(self.data) - 1)].get('price', 100)
        
        reward = 0
        
        # Execute action
        if action == 0 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = current_price
            reward = -0.5  # Small cost
        elif action == 1 and self.position == 0:  # SELL
            self.position = -1
            self.entry_price = current_price
            reward = -0.5
        elif action == 0 and self.position == -1:  # Close short
            pnl = (self.entry_price - current_price) / self.entry_price
            reward = pnl * 100
            self.position = 0
        elif action == 1 and self.position == 1:  # Close long
            pnl = (current_price - self.entry_price) / self.entry_price
            reward = pnl * 100
            self.position = 0
        
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1
        
        next_state = self._get_state()
        
        return next_state, reward, done


class WalkForwardRetrainer:
    """Main orchestrator for walk-forward retraining"""
    
    def __init__(self, config: Optional[RetrainConfig] = None):
        self.config = config or RetrainConfig()
        self.data_loader = DataLoader()
        self.last_retrain = None
        self.current_model_performance = None
        self.best_model_performance = None
        self.is_running = False
        self._thread = None
        
        # Create directories
        os.makedirs(self.config.model_dir, exist_ok=True)
        os.makedirs(self.config.backup_dir, exist_ok=True)
        
        # Load previous performance
        self._load_performance_history()
    
    def _load_performance_history(self):
        """Load performance history from file"""
        history_path = os.path.join(self.config.model_dir, 'performance_history.json')
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    self.performance_history = json.load(f)
            except:
                self.performance_history = []
        else:
            self.performance_history = []
    
    def _save_performance_history(self):
        """Save performance history to file"""
        history_path = os.path.join(self.config.model_dir, 'performance_history.json')
        with open(history_path, 'w') as f:
            json.dump(self.performance_history, f, indent=2)
    
    def evaluate_model(self, model: PolicyNetwork, val_df: pd.DataFrame) -> Dict:
        """Evaluate model performance on validation data"""
        model.eval()
        predictions = []
        actuals = []
        
        for _, row in val_df.iterrows():
            features = np.array([
                row.get('rsi', 50) / 100,
                min(1.0, row.get('volume_ratio', 1.0) / 2),
                min(1.0, row.get('volatility', 0.01) * 100),
                min(0.05, row.get('supply_distance', 0.005)) * 200,
                min(0.05, row.get('demand_distance', 0.005)) * 200,
                row.get('manipulation_score', 0.5),
                row.get('zone_strength', 50) / 100,
                min(1.0, row.get('touches', 3) / 10),
                min(1.0, row.get('hidden_funds_estimate', 50000) / 100000),
                0, 0, 0
            ], dtype=np.float32)
            
            with torch.no_grad():
                features_t = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
                logits = model(features_t)
                action = torch.argmax(logits, dim=1).item()
            
            predictions.append(action)
            actual = {'BUY': 0, 'SELL': 1, 'HOLD': 2}.get(row.get('consensus_action', 'HOLD'), 2)
            actuals.append(actual)
        
        # Calculate metrics
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        accuracy = (predictions == actuals).mean()
        
        # Simplified Sharpe simulation
        returns = []
        for i in range(len(predictions) - 1):
            if predictions[i] == 0:  # BUY
                ret = val_df.iloc[i+1].get('actual_outcome', 0)
                returns.append(ret)
            elif predictions[i] == 1:  # SELL
                ret = -val_df.iloc[i+1].get('actual_outcome', 0)
                returns.append(ret)
        
        if len(returns) > 1:
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)
        else:
            sharpe = 0
        
        win_rate = np.mean([r > 0 for r in returns]) if returns else 0
        
        return {
            'accuracy': accuracy,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'num_trades': len(returns),
            'total_return': np.sum(returns)
        }
    
    def should_retrain(self) -> bool:
        """Check if retraining is needed"""
        if self.last_retrain is None:
            return True
        
        days_since = (datetime.now() - self.last_retrain).days
        return days_since >= self.config.retrain_days
    
    def retrain(self, force: bool = False) -> Dict:
        """Run complete walk-forward retraining"""
        if not force and not self.should_retrain():
            logger.info("Not yet time for retraining")
            return {'retrained': False, 'reason': 'Not enough time elapsed'}
        
        logger.info("=" * 60)
        logger.info("STARTING WALK-FORWARD RETRAINING")
        logger.info("=" * 60)
        
        end_date = datetime.now()
        
        # Load data
        train_df, val_df = self.data_loader.get_training_data(
            end_date,
            self.config.training_window_days,
            self.config.validation_window_days
        )
        
        if len(train_df) < 100:
            logger.warning("Insufficient training data")
            return {'retrained': False, 'reason': 'Insufficient training data'}
        
        # Backup current model if exists
        current_model_path = os.path.join(self.config.model_dir, 'current_model.pt')
        if os.path.exists(current_model_path):
            backup_path = os.path.join(self.config.backup_dir, f'model_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pt')
            import shutil
            shutil.copy(current_model_path, backup_path)
            logger.info(f"Backed up current model to {backup_path}")
        
        # Step 1: HA3C Pretraining
        pretrainer = HA3CPretrainer(self.config)
        pretrain_result = pretrainer.train(train_df, val_df)
        
        # Load best pretrained model
        best_pretrain_path = os.path.join(self.config.model_dir, 'best_pretrain.pt')
        checkpoint = torch.load(best_pretrain_path)
        policy = PolicyNetwork(self.config.input_dim, self.config.hidden_dim, self.config.output_dim)
        policy.load_state_dict(checkpoint['policy_state_dict'])
        
        # Step 2: A2C Fine-tuning
        env = TradingEnvironment(train_df)
        fine_tuner = A2CFineTuner(self.config, policy)
        a2c_result = fine_tuner.train(env, episodes=self.config.epochs_a2c)
        
        # Step 3: Evaluate new model
        new_performance = self.evaluate_model(policy, val_df)
        logger.info(f"New model performance: {new_performance}")
        
        # Step 4: Compare with current model
        should_deploy = True
        
        if self.current_model_performance:
            sharpe_drop = (self.current_model_performance['sharpe_ratio'] - new_performance['sharpe_ratio']) / (abs(self.current_model_performance['sharpe_ratio']) + 1e-10)
            
            if sharpe_drop > self.config.max_performance_drop:
                logger.warning(f"Performance dropped {sharpe_drop:.1%} - not deploying")
                should_deploy = False
            
            if new_performance['sharpe_ratio'] < self.config.min_validation_sharpe:
                logger.warning(f"Sharpe {new_performance['sharpe_ratio']:.2f} below threshold - not deploying")
                should_deploy = False
            
            if new_performance['win_rate'] < self.config.min_validation_win_rate:
                logger.warning(f"Win rate {new_performance['win_rate']:.1%} below threshold - not deploying")
                should_deploy = False
        
        # Step 5: Deploy or rollback
        result = {
            'retrained': True,
            'deployed': should_deploy,
            'pretrain_accuracy': pretrain_result['best_accuracy'],
            'a2c_avg_reward': a2c_result['final_avg_reward'],
            'new_performance': new_performance,
            'old_performance': self.current_model_performance
        }
        
        if should_deploy:
            # Save as current model
            torch.save(policy.state_dict(), current_model_path)
            self.current_model_performance = new_performance
            
            # Update best model if better
            if (self.best_model_performance is None or 
                new_performance['sharpe_ratio'] > self.best_model_performance['sharpe_ratio']):
                self.best_model_performance = new_performance
                shutil.copy(current_model_path, os.path.join(self.config.model_dir, 'best_model.pt'))
                logger.info("New best model saved!")
            
            logger.info("✅ New model deployed successfully")
        else:
            # Rollback to previous model
            if os.path.exists(backup_path):
                shutil.copy(backup_path, current_model_path)
                logger.info("Rolled back to previous model")
        
        # Update history
        self.performance_history.append({
            'timestamp': datetime.now().isoformat(),
            'deployed': should_deploy,
            'performance': new_performance
        })
        self._save_performance_history()
        
        self.last_retrain = datetime.now()
        
        return result
    
    def start_auto_retrain(self, check_interval_hours: int = 1):
        """Start automatic retraining in background"""
        if self.is_running:
            return
        
        self.is_running = True
        
        def retrain_loop():
            while self.is_running:
                try:
                    if self.should_retrain():
                        self.retrain()
                    time.sleep(check_interval_hours * 3600)
                except Exception as e:
                    logger.error(f"Auto-retrain error: {e}")
                    time.sleep(3600)
        
        self._thread = threading.Thread(target=retrain_loop, daemon=True)
        self._thread.start()
        logger.info(f"Auto-retrain started (check every {check_interval_hours} hours)")
    
    def stop_auto_retrain(self):
        """Stop automatic retraining"""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-retrain stopped")


# ============================================================
# Main Execution
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("WALK-FORWARD RETRAINING PIPELINE")
    print("=" * 60)
    
    # Initialize retrainer
    retrainer = WalkForwardRetrainer()
    
    # Run retraining
    result = retrainer.retrain(force=True)
    
    print("\n" + "=" * 60)
    print("RETRAINING RESULT")
    print("=" * 60)
    print(json.dumps(result, indent=2, default=str))
    
    # Start auto-retraining (uncomment for production)
    # retrainer.start_auto_retrain(check_interval_hours=1)
    # 
    # try:
    #     while True:
    #         time.sleep(60)
    # except KeyboardInterrupt:
    #     retrainer.stop_auto_retrain()
