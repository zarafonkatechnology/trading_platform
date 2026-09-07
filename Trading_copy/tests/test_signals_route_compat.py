from fastapi.testclient import TestClient

from src.api.main import app


def test_signals_ping_is_available_at_root_compatibility_paths():
    client = TestClient(app)

    for path in ["/signals/ping", "/client/signals/ping"]:
        response = client.get(path)
        assert response.status_code == 200, f"Expected 200 for {path}, got {response.status_code}"
