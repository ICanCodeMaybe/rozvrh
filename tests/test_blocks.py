import os

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

API_KEY = "test-key-12345"
VALID = {"start": "2026-09-07T14:30", "end": "2026-09-07T15:30", "label": "Lunch", "color": "#4a90d9"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ROZVRH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ROZVRH_API_KEY", API_KEY)
    return TestClient(create_app())


def headers(key=API_KEY):
    return {"X-API-Key": key}


def test_create_and_get_block(client):
    resp = client.post("/api/blocks", json=VALID, headers=headers())
    assert resp.status_code == 201
    block = resp.json()
    assert block["label"] == "Lunch"
    assert block["source"] == "ui"

    resp = client.get("/api/blocks", params={"from": "2026-09-07T00:00", "to": "2026-09-08T00:00"}, headers=headers())
    assert resp.status_code == 200
    assert [b["id"] for b in resp.json()] == [block["id"]]


def test_get_range_excludes_non_overlapping(client):
    client.post("/api/blocks", json=VALID, headers=headers())
    resp = client.get("/api/blocks", params={"from": "2026-09-08T00:00", "to": "2026-09-09T00:00"}, headers=headers())
    assert resp.status_code == 200
    assert resp.json() == []


def test_patch_block(client):
    block = client.post("/api/blocks", json=VALID, headers=headers()).json()
    resp = client.patch(f"/api/blocks/{block['id']}", json={"label": "Moved", "start": "2026-09-07T16:00", "end": "2026-09-07T17:00"}, headers=headers())
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["label"] == "Moved"
    assert updated["start"] == "2026-09-07T16:00"


def test_patch_nonexistent_block(client):
    resp = client.patch("/api/blocks/999", json={"label": "x"}, headers=headers())
    assert resp.status_code == 404


def test_delete_block(client):
    block = client.post("/api/blocks", json=VALID, headers=headers()).json()
    resp = client.delete(f"/api/blocks/{block['id']}", headers=headers())
    assert resp.status_code == 204
    resp = client.get("/api/blocks", params={"from": "2026-09-07T00:00", "to": "2026-09-08T00:00"}, headers=headers())
    assert resp.json() == []


def test_delete_nonexistent_block(client):
    resp = client.delete("/api/blocks/999", headers=headers())
    assert resp.status_code == 404


def test_422_on_end_before_start(client):
    resp = client.post("/api/blocks", json={"start": "2026-09-07T15:00", "end": "2026-09-07T14:00"}, headers=headers())
    assert resp.status_code == 422


def test_422_on_bad_alignment(client):
    resp = client.post("/api/blocks", json={"start": "2026-09-07T14:10", "end": "2026-09-07T15:00"}, headers=headers())
    assert resp.status_code == 422


def test_422_on_bad_color(client):
    resp = client.post("/api/blocks", json={**VALID, "color": "blue"}, headers=headers())
    assert resp.status_code == 422


def test_422_on_label_too_long(client):
    resp = client.post("/api/blocks", json={**VALID, "label": "x" * 201}, headers=headers())
    assert resp.status_code == 422


def test_patch_respecting_start_end_validation(client):
    block = client.post("/api/blocks", json=VALID, headers=headers()).json()
    resp = client.patch(f"/api/blocks/{block['id']}", json={"end": "2026-09-07T10:00"}, headers=headers())
    assert resp.status_code == 422


def test_get_range_from_after_to(client):
    resp = client.get("/api/blocks", params={"from": "2026-09-08T00:00", "to": "2026-09-07T00:00"}, headers=headers())
    assert resp.status_code == 422


def test_401_without_key(client):
    resp = client.get("/api/blocks", params={"from": "2026-09-07T00:00", "to": "2026-09-08T00:00"})
    assert resp.status_code == 401


def test_401_with_wrong_key(client):
    resp = client.get("/api/blocks", params={"from": "2026-09-07T00:00", "to": "2026-09-08T00:00"}, headers=headers("nope"))
    assert resp.status_code == 401


def test_401_on_post_without_key(client):
    resp = client.post("/api/blocks", json=VALID)
    assert resp.status_code == 401


# --- To-do blocks (source="todo": unscheduled, keeps slot + duration) ---


def test_create_todo_block_keeps_slot_and_duration(client):
    resp = client.post("/api/blocks", json={"start": "2026-09-07T08:00", "end": "2026-09-07T09:30", "label": "Someday", "source": "todo"}, headers=headers())
    assert resp.status_code == 201
    block = resp.json()
    assert block["source"] == "todo"
    assert block["start"] == "2026-09-07T08:00"
    assert block["end"] == "2026-09-07T09:30"


def test_todo_blocks_excluded_from_range_and_week(client):
    client.post("/api/blocks", json={"start": "2026-09-07T10:00", "end": "2026-09-07T11:00", "label": "T", "source": "todo"}, headers=headers())
    resp = client.get("/api/blocks", params={"from": "2026-09-07T00:00", "to": "2026-09-08T00:00"}, headers=headers())
    assert resp.json() == []
    resp = client.get("/api/weeks/2026/37", headers=headers())
    assert resp.json() == []


def test_todo_list_returns_todo_blocks_only(client):
    client.post("/api/blocks", json=VALID, headers=headers())
    todo = client.post("/api/blocks", json={"start": "2026-09-07T08:00", "end": "2026-09-07T09:00", "label": "Someday", "source": "todo"}, headers=headers()).json()
    resp = client.get("/api/blocks/todo", headers=headers())
    assert resp.status_code == 200
    assert [b["id"] for b in resp.json()] == [todo["id"]]


def test_schedule_todo_block_via_patch(client):
    todo = client.post("/api/blocks", json={"start": "2026-09-07T08:00", "end": "2026-09-07T09:00", "label": "Someday", "source": "todo"}, headers=headers()).json()
    resp = client.patch(f"/api/blocks/{todo['id']}", json={"start": "2026-09-08T14:00", "end": "2026-09-08T15:00"}, headers=headers())
    assert resp.status_code == 200
    scheduled = resp.json()
    assert scheduled["source"] == "ui"
    resp = client.get("/api/weeks/2026/37", headers=headers())
    assert [b["id"] for b in resp.json()] == [todo["id"]]


def test_schedule_todo_block_start_only_keeps_duration(client):
    # moving by start alone: 1h duration is preserved via end = start + duration
    todo = client.post("/api/blocks", json={"start": "2026-09-07T08:00", "end": "2026-09-07T09:00", "label": "Someday", "source": "todo"}, headers=headers()).json()
    resp = client.patch(f"/api/blocks/{todo['id']}", json={"start": "2026-09-08T14:00"}, headers=headers())
    assert resp.status_code == 200
    scheduled = resp.json()
    assert scheduled["start"] == "2026-09-08T14:00"
    assert scheduled["end"] == "2026-09-08T15:00"
    assert scheduled["source"] == "ui"


def test_unschedule_block_preserves_duration(client):
    block = client.post("/api/blocks", json=VALID, headers=headers()).json()
    resp = client.patch(f"/api/blocks/{block['id']}", json={"source": "todo"}, headers=headers())
    assert resp.status_code == 200
    unscheduled = resp.json()
    assert unscheduled["source"] == "todo"
    # slot and duration survive the round-trip
    assert unscheduled["start"] == "2026-09-07T14:30"
    assert unscheduled["end"] == "2026-09-07T15:30"
    resp = client.get("/api/weeks/2026/37", headers=headers())
    assert resp.json() == []
    resp = client.get("/api/blocks/todo", headers=headers())
    assert [b["id"] for b in resp.json()] == [block["id"]]


def test_422_on_invalid_source(client):
    resp = client.post("/api/blocks", json={**VALID, "source": "ics:fake"}, headers=headers())
    assert resp.status_code == 422


def test_401_on_todo_list_without_key(client):
    assert client.get("/api/blocks/todo").status_code == 401
