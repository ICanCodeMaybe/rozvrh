import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

API_KEY = "test-key-12345"
# Monday of ISO week 37, 2026; day_of_week 0 = Monday .. 6 = Sunday
MONDAY = "2026-09-07"
TEMPLATE = {
    "name": "Work week",
    "blocks": [
        {"day_of_week": 0, "start_time": "09:00", "end_time": "10:00", "label": "Standup", "color": "#4a90d9"},
        {"day_of_week": 1, "start_time": "09:00", "end_time": "10:00", "label": "Standup", "color": "#4a90d9"},
    ],
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ROZVRH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ROZVRH_API_KEY", API_KEY)
    return TestClient(create_app())


def headers(key=API_KEY):
    return {"X-API-Key": key}


def create_template(client, payload=None):
    resp = client.post("/api/templates", json=payload or TEMPLATE, headers=headers())
    assert resp.status_code == 201
    return resp.json()


def list_week_blocks(client, year=2026, week=37):
    return client.get(f"/api/weeks/{year}/{week}", headers=headers()).json()


def test_template_crud_roundtrip(client):
    created = create_template(client)
    assert created["name"] == "Work week"
    assert len(created["blocks"]) == 2
    assert created["blocks"][0]["day_of_week"] == 0

    listed = client.get("/api/templates", headers=headers()).json()
    assert [t["id"] for t in listed] == [created["id"]]

    replaced = client.put(
        f"/api/templates/{created['id']}",
        json={"name": "Gym", "blocks": [{"day_of_week": 5, "start_time": "18:00", "end_time": "19:00"}]},
        headers=headers(),
    )
    assert replaced.status_code == 200
    body = replaced.json()
    assert body["name"] == "Gym"
    assert len(body["blocks"]) == 1

    deleted = client.delete(f"/api/templates/{created['id']}", headers=headers())
    assert deleted.status_code == 204
    assert client.get("/api/templates", headers=headers()).json() == []


def test_template_404_on_put_and_delete(client):
    payload = {"name": "X", "blocks": []}
    assert client.put("/api/templates/999", json=payload, headers=headers()).status_code == 404
    assert client.delete("/api/templates/999", headers=headers()).status_code == 404


def test_template_422_on_bad_block(client):
    bad = {"name": "X", "blocks": [{"day_of_week": 7, "start_time": "09:00", "end_time": "10:00"}]}
    assert client.post("/api/templates", json=bad, headers=headers()).status_code == 422
    bad = {"name": "X", "blocks": [{"day_of_week": 0, "start_time": "10:00", "end_time": "09:00"}]}
    assert client.post("/api/templates", json=bad, headers=headers()).status_code == 422
    bad = {"name": "X", "blocks": [{"day_of_week": 0, "start_time": "09:1", "end_time": "10:00"}]}
    bad_align = {"name": "X", "blocks": [{"day_of_week": 0, "start_time": "09:07", "end_time": "10:00"}]}
    assert client.post("/api/templates", json=bad, headers=headers()).status_code == 422
    assert client.post("/api/templates", json=bad_align, headers=headers()).status_code == 422


def test_apply_to_empty_week_creates_blocks(client):
    template = create_template(client)
    resp = client.post(f"/api/templates/{template['id']}/apply/2026/37", headers=headers())
    assert resp.status_code == 200
    created = resp.json()
    assert len(created) == 2
    assert created[0]["start"] == f"{MONDAY}T09:00"
    assert created[1]["start"] == "2026-09-08T09:00"
    assert len(list_week_blocks(client)) == 2


def test_apply_skips_occupied_slots(client):
    template = create_template(client)
    # occupy Monday 09:30-10:30, which overlaps the template's Monday 09:00-10:00
    resp = client.post(
        "/api/blocks",
        json={"start": f"{MONDAY}T09:30", "end": f"{MONDAY}T10:30", "label": "Busy"},
        headers=headers(),
    )
    assert resp.status_code == 201

    resp = client.post(f"/api/templates/{template['id']}/apply/2026/37", headers=headers())
    assert resp.status_code == 200
    created = resp.json()
    assert [b["start"] for b in created] == ["2026-09-08T09:00"]

    blocks = list_week_blocks(client)
    assert sorted(b["start"] for b in blocks) == [f"{MONDAY}T09:30", "2026-09-08T09:00"]


def test_apply_does_not_skip_adjacent_block(client):
    template = create_template(
        client,
        {"name": "T", "blocks": [{"day_of_week": 0, "start_time": "10:00", "end_time": "11:00"}]},
    )
    client.post(
        "/api/blocks",
        json={"start": f"{MONDAY}T09:00", "end": f"{MONDAY}T10:00"},
        headers=headers(),
    )
    resp = client.post(f"/api/templates/{template['id']}/apply/2026/37", headers=headers())
    assert len(resp.json()) == 1


def test_apply_twice_is_idempotent(client):
    template = create_template(client)
    client.post(f"/api/templates/{template['id']}/apply/2026/37", headers=headers())
    resp = client.post(f"/api/templates/{template['id']}/apply/2026/37", headers=headers())
    assert resp.json() == []
    assert len(list_week_blocks(client)) == 2


def test_apply_404_unknown_template(client):
    assert client.post("/api/templates/999/apply/2026/37", headers=headers()).status_code == 404


def test_apply_422_bad_week(client):
    template = create_template(client)
    assert client.post(f"/api/templates/{template['id']}/apply/2026/54", headers=headers()).status_code == 422
    assert client.post(f"/api/templates/{template['id']}/apply/2025/53", headers=headers()).status_code == 422


def test_template_401_without_key(client):
    assert client.get("/api/templates").status_code == 401


def test_template_401_with_wrong_key(client):
    assert client.post("/api/templates", json=TEMPLATE, headers=headers("nope")).status_code == 401


def test_apply_401_without_key(client):
    assert client.post("/api/templates/1/apply/2026/37").status_code == 401
