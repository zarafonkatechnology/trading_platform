def calculate_zscore(self, symbol: str, price: float) -> Dict:
    """Calculate Z-score using rolling window (NOT fixed baseline)"""
    self.update_price(symbol, price)
    
    samples = self.samples.get(symbol, 0)
    if samples < 20:
        return {
            'z_score': 0,
            'action': 'HOLD',
            'confidence': 0,
            'samples': samples,
            'reasoning': f'Building history: {samples}/20'
        }
    
    # ===== USE ROLLING WINDOW (NOT fixed baseline) =====
    history = list(self.price_history[symbol])
    
    # Use last N samples for calculation (e.g., last 20-30)
    lookback = min(30, len(history))
    recent_history = history[-lookback:]
    
    mean = sum(recent_history) / len(recent_history)
    variance = sum((x - mean) ** 2 for x in recent_history) / len(recent_history)
    std = math.sqrt(variance) if variance > 0 else 0.0001
    
    # Calculate Z-score
    z_score = (price - mean) / std if std > 0 else 0
    self.z_score[symbol] = z_score
    self.mean[symbol] = mean
    self.std[symbol] = std
    
    entry_threshold, exit_threshold = self.get_thresholds(symbol)
    
    # Determine action
    if z_score > entry_threshold:
        return {
            'z_score': z_score,
            'action': 'SELL',
            'confidence': min(95, 75 + (z_score - entry_threshold) * 15),
            'mean': mean,
            'std': std,
            'samples': samples,
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'reasoning': f'Overbought: Z={z_score:.2f}'
        }
    elif z_score < -entry_threshold:
        return {
            'z_score': z_score,
            'action': 'BUY',
            'confidence': min(95, 75 + (-z_score - entry_threshold) * 15),
            'mean': mean,
            'std': std,
            'samples': samples,
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'reasoning': f'Oversold: Z={z_score:.2f}'
        }
    else:
        return {
            'z_score': z_score,
            'action': 'HOLD'
            'confidence': max(40, 50 - abs(z_score) * 5),
            'mean': mean,
            'std': std,
            'samples': samples,
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'reasoning': f'Normal: Z={z_score:.2f}'
        }