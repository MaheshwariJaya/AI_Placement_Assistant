"""Test Health and API Root endpoints using genuine ASGI HTTP request pipeline."""
import json
from unittest.mock import AsyncMock, patch
import pytest

from app.config import get_settings
from app.main import app
from app.routes.health import liveness_probe, readiness_probe

settings = get_settings()


def _run_coroutine_sync(coro):
    """Utility to step a coroutine to completion synchronously."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


def asgi_http_request(app_instance, path: str, method: str = "GET", headers=None):
    """
    Execute a genuine ASGI HTTP request through the FastAPI application pipeline,
    exercising Starlette routing, CORS middleware, response serialization,
    status codes, and headers without opening OS network sockets.
    """
    response_meta = {}
    response_chunks = bytearray()

    raw_headers = [(k.lower().encode("latin1"), v.encode("latin1")) for k, v in (headers or {}).items()]
    if not any(k == b"host" for k, _ in raw_headers):
        raw_headers.append((b"host", b"localhost"))
    if not any(k == b"accept" for k, _ in raw_headers):
        raw_headers.append((b"accept", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("localhost", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            response_meta["status"] = message["status"]
            response_meta["headers"] = dict(
                (k.decode("latin1"), v.decode("latin1")) for k, v in message.get("headers", [])
            )
        elif message["type"] == "http.response.body":
            response_chunks.extend(message.get("body", b""))

    _run_coroutine_sync(app_instance(scope, receive, send))

    body_bytes = bytes(response_chunks)
    json_data = json.loads(body_bytes.decode("utf-8")) if body_bytes else None

    return {
        "status_code": response_meta.get("status"),
        "headers": response_meta.get("headers", {}),
        "data": json_data,
    }


# =============================================================================
# Genuine HTTP / ASGI Integration Tests
# =============================================================================

def test_http_health_live_integration():
    """
    Verify genuine HTTP request to /health/live:
    - HTTP 200 response status
    - JSON serialization
    - Expected response fields (success, status, timestamp, app, environment)
    - Route registered correctly on application router
    """
    res = asgi_http_request(app, "/health/live")
    assert res["status_code"] == 200
    assert "application/json" in res["headers"].get("content-type", "")
    data = res["data"]
    assert data["success"] is True
    assert data["status"] == "alive"
    assert "timestamp" in data
    assert data["app"] == settings.APP_NAME
    assert data["environment"] == settings.APP_ENV


def test_http_api_v1_health_live_integration():
    """Verify genuine HTTP request to prefix route /api/v1/health/live."""
    res = asgi_http_request(app, "/api/v1/health/live")
    assert res["status_code"] == 200
    assert res["data"]["status"] == "alive"
    assert res["data"]["app"] == settings.APP_NAME


def test_http_root_endpoint_integration():
    """Verify genuine HTTP request to root '/' endpoint and metadata serialization."""
    res = asgi_http_request(app, "/")
    assert res["status_code"] == 200
    data = res["data"]
    assert data["name"] == settings.APP_NAME
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"
    assert data["health_live"] == "/health/live"
    assert data["api_v1_prefix"] == settings.API_V1_PREFIX


def test_http_health_ready_connected_integration():
    """Verify genuine HTTP request to /health/ready with healthy database."""
    mock_db = {
        "connected": True,
        "database": "placement_intelligence_local",
        "schema": "placement_app_v2",
        "host": "localhost",
        "latency_ms": 1.2,
        "error": None,
    }
    with patch("app.routes.health.check_database_connection", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_db
        res = asgi_http_request(app, "/health/ready")
        assert res["status_code"] == 200
        data = res["data"]
        assert data["success"] is True
        assert data["status"] == "ready"
        assert data["database"]["status"] == "connected"
        assert data["database"]["database_name"] == "placement_intelligence_local"


def test_http_health_ready_degraded_integration():
    """Verify genuine HTTP request to /health/ready returning 503 on database disconnection."""
    mock_db = {
        "connected": False,
        "database": "placement_intelligence_local",
        "host": "localhost",
        "latency_ms": 45.0,
        "error": "Connection refused",
    }
    with patch("app.routes.health.check_database_connection", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_db
        res = asgi_http_request(app, "/health/ready")
        assert res["status_code"] == 503
        data = res["data"]
        assert data["success"] is False
        assert data["status"] == "degraded"
        assert data["database"]["status"] == "disconnected"
        assert "error" in data["database"]
        assert "remedy" in data["database"]


def test_health_live_direct_function():
    """Direct invocation test ensuring function logic is intact."""
    data = _run_coroutine_sync(liveness_probe())
    assert data["success"] is True
    assert data["status"] == "alive"
    assert data["app"] == settings.APP_NAME
