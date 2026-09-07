import sys
sys.path.insert(0, 'Trading_copy')
from src.api.main import app

for r in app.routes:
    print(r.path, sorted(getattr(r, 'methods', [])), getattr(r, 'name', None))
