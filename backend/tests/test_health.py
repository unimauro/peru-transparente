from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_openapi_lists_v1_routes():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/entities" in paths
    assert "/api/v1/officials" in paths
    assert "/api/v1/graph/neighborhood/{node_id}" in paths
