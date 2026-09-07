from fastapi.testclient import TestClient

from src.api.main import app


def test_client_registration_and_login_persist_to_database():
    with TestClient(app) as client:
        register_response = client.post(
            "/api/v1/client/register",
            json={
                "full_name": "DB User",
                "email": "dbuser@example.com",
                "password": "secret123",
            },
        )

        assert register_response.status_code == 200, register_response.text
        register_payload = register_response.json()
        assert register_payload["success"] is True
        assert register_payload["user"]["email"] == "dbuser@example.com"
        assert register_payload["user"]["full_name"] == "DB User"

        login_response = client.post(
            "/api/v1/client/login",
            json={
                "email": "dbuser@example.com",
                "password": "secret123",
            },
        )

        assert login_response.status_code == 200, login_response.text
        login_payload = login_response.json()
        assert login_payload["access_token"]
        assert login_payload["user"]["email"] == "dbuser@example.com"
