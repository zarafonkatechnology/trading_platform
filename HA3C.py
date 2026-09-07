import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# 1. Load expert data
df = pd.read_csv('expert_data.csv')
features = ['rsi', 'volume_ratio', 'volatility', 'supply_distance', 'demand_distance', 'manipulation_score']
X = df[features].values
y = pd.Categorical(df['expert_action']).codes  # BUY=0, SELL=1, HOLD=2

# 2. Train/val split
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# 3. Standardize
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_val = scaler.transform(X_val)

# 4. Simple neural network
class PolicyNetwork(nn.Module):
    def __init__(self, input_dim=6, hidden_dim=64, output_dim=3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
            nn.Softmax(dim=-1)
        )
    def forward(self, x):
        return self.net(x)

model = PolicyNetwork()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 5. Training loop
batch_size = 32
train_loader = DataLoader(TensorDataset(torch.tensor(X_train, dtype=torch.float32),
                                        torch.tensor(y_train, dtype=torch.long)),
                          batch_size=batch_size, shuffle=True)

for epoch in range(100):
    for xb, yb in train_loader:
        optimizer.zero_grad()
        pred = model(xb)
        loss = criterion(pred, yb)
        loss.backward()
        optimizer.step()
    # Validation accuracy
    with torch.no_grad():
        val_pred = model(torch.tensor(X_val, dtype=torch.float32))
        val_acc = (val_pred.argmax(1) == torch.tensor(y_val)).float().mean().item()
    if epoch % 10 == 0:
        print(f"Epoch {epoch}, Val Acc: {val_acc:.3f}")

# Save pretrained model
torch.save(model.state_dict(), 'pretrained_policy.pt')
print("✅ Pretrained policy saved.")
