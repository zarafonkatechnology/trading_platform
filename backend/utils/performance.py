import time
from functools import wraps

def measure_time(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000  # milliseconds
        print(f"⏱️ {func.__name__}: {elapsed:.2f}ms")
        return result
    return wrapper

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {}
    
    def record(self, name, elapsed_ms):
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(elapsed_ms)
    
    def report(self):
        print("\n📊 Performance Report")
        print("=" * 40)
        for name, times in self.metrics.items():
            avg = sum(times) / len(times)
            print(f"{name}: avg={avg:.2f}ms, count={len(times)}")
