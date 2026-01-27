import numpy as np

def MA(data, n):
    return np.mean(data[-n:])

def RSI(data, n=14):
    diff = np.diff(data[-(n+1):])
    up = diff[diff > 0].sum()
    down = -diff[diff < 0].sum()
    if down == 0:
        return 100
    rs = up / down
    return 100 - 100 / (1 + rs)

def ATR(high, low, close, n=14):
    tr = np.maximum(
        high[-n:] - low[-n:],
        np.abs(high[-n:] - close[-n-1:-1]),
        np.abs(low[-n:] - close[-n-1:-1])
    )
    return np.mean(tr)
