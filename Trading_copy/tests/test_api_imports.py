import importlib
import sys
from pathlib import Path


def test_api_module_imports_without_signal_service_error():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    module = importlib.import_module("src.api.main")

    assert module.app is not None


def test_websocket_signal_route_is_registered():
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    module = importlib.import_module("src.api.main")
    route_paths = {route.path for route in module.app.routes if hasattr(route, "path")}

    assert "/ws/signals/{client_id}" in route_paths
