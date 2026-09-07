import pandas as pd
import numpy as np

def calculate_rsi(prices, period=14):
    """Relative Strength Index"""
    delta = pd.Series(prices).diff()
    gain = delta.clip(lower=0).rolling(window=period).mean()
    loss = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def calculate_moving_average(prices, period=20):
    return pd.Series(prices).rolling(window=period).mean().iloc[-1]

def calculate_ichimoku(high, low, close, tenkan=9, kijun=26, senkou_b=52):
    """Basic Ichimoku components"""
    tenkan_sen = (pd.Series(high).rolling(tenkan).max() + 
                  pd.Series(low).rolling(tenkan).min()) / 2
    kijun_sen = (pd.Series(high).rolling(kijun).max() + 
                 pd.Series(low).rolling(kijun).min()) / 2
    senkou_span_a = (tenkan_sen + kijun_sen) / 2
    senkou_span_b = (pd.Series(high).rolling(senkou_b).max() + 
                     pd.Series(low).rolling(senkou_b).min()) / 2
    
    return {
        'tenkan': tenkan_sen.iloc[-1],
        'kijun': kijun_sen.iloc[-1],
        'senkou_a': senkou_span_a.iloc[-1],
        'senkou_b': senkou_span_b.iloc[-1],
        'cloud_top': max(senkou_span_a.iloc[-1], senkou_span_b.iloc[-1]),
        'cloud_bottom': min(senkou_span_a.iloc[-1], senkou_span_b.iloc[-1])
    }
