"""Unit tests for Campus Pulse.

Run with:  pytest -v
These tests are the quality gate in CI: if ANY test fails, the pipeline stops
and no Docker image is published or deployed.

Flask's built-in test client sends requests directly to the app in memory,
so no server needs to be running.
"""
import pytest

from app.main import create_app


@pytest.fixture
def client():
    """A fresh app (empty task list, auth disabled) for every test."""
    return create_app(api_key="").test_client()


def test_health(client):
    """The probes depend on this endpoint, so it must always return 200 + ok."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_version_reads_environment(client, monkeypatch):
    """/version must reflect the APP_VERSION environment variable.

    monkeypatch temporarily sets an env var for just this test.
    """
    monkeypatch.setenv("APP_VERSION", "9.9.9")
    assert client.get("/version").get_json()["version"] == "9.9.9"


def test_create_and_fetch_task(client):
    """Happy path: create a task, then read it back."""
    created = client.post("/tasks", json={"title": "Revise Docker", "course": "Infra"})
    assert created.status_code == 201
    task_id = created.get_json()["id"]
    fetched = client.get(f"/tasks/{task_id}")
    assert fetched.get_json()["title"] == "Revise Docker"


def test_title_is_required(client):
    """Validation: an empty body must be rejected with 400 Bad Request."""
    assert client.post("/tasks", json={}).status_code == 400


def test_complete_and_delete_task(client):
    """Full lifecycle: create -> mark done -> delete -> confirm it is gone."""
    task_id = client.post("/tasks", json={"title": "Lab 3"}).get_json()["id"]
    assert client.put(f"/tasks/{task_id}/done").get_json()["done"] is True
    assert client.delete(f"/tasks/{task_id}").status_code == 204
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_write_requires_api_key_when_configured():
    """Security: with an API key set, writes without the header get 401."""
    secured = create_app(api_key="s3cret").test_client()
    assert secured.post("/tasks", json={"title": "x"}).status_code == 401
    ok = secured.post("/tasks", json={"title": "x"}, headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 201


def test_stats_with_tasks(client):
    """Stats reflect created and completed tasks."""
    task_id = client.post("/tasks", json={"title": "a"}).get_json()["id"]
    client.put(f"/tasks/{task_id}/done")
    assert client.get("/stats").get_json() == {"total": 1, "done": 2, "completion_rate": 100.0}
