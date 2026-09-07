import sys
sys.path.insert(0, 'c:/trading_platform')
from Trading_copy.src.api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
for path in ['/signals/ping', '/client/signals/ping', '/api/v1/signals/ping']:
    response = client.get(path)
    print(path, response.status_code, response.text)
