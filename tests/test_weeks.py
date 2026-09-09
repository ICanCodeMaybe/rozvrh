import pytest
from fastapi.testclient import TestClient

from backend.main import create_app

API_KEY = "test-key-12345"
MONDAY = "2026-09-07"  # Monday of ISO week 37, 2026


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ROZVRH_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("ROZVRH_API_KEY", API_KEY)
    return TestClient(create_app())


def headers(key=API_KEY):
    return {"X-API-Key": key}


def make_block(client, start, end):
    resp = client.post(
        "/api/blocks", json={"start": start, "end": end, "label": "B"}, headers=headers()
    )
    assert resp.status_code == 201
    return resp.json()


def test_week_returns_overlapping_blocks(client):
    make_block(client, f"{MONDAY}T10:00", f"{MONDAY}T11:00")
    # straddles the week boundary: starts Sunday before, ends Monday morning
    make_block(client, "2026-09-06T23:00", f"{MONDAY}T01:00")
    # entirely outside the week
    make_block(client, "2026-09-14T10:00", "2026-09-14T11:00")

    resp = client.get("/api/weeks/2026/37", headers=headers())
    assert resp.status_code == 200
    blocks = resp.json()
    assert len(blocks) == 2
    starts = sorted(b["start"] for b in blocks)
    assert starts == ["2026-09-06T23:00", f"{MONDAY}T10:00"]


def test_week_empty(client):
    resp = client.get("/api/weeks/2026/40", headers=headers())
    assert resp.status_code == 200
    assert resp.json() == []


def test_week_iso_boundary_week1(client):
    # 2027-01-04 is the Monday of ISO week 1 of 2027; a block on Jan 3 belongs to 2026-W53
    make_block(client, "2027-01-04T09:00", "2027-01-04T10:00")
    resp = client.get("/api/weeks/2027/1", headers=headers())
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_week_block_on_sunday(client):
    # last day of ISO week 37 is 2026-09-13
    make_block(client, "2026-09-13T20:00", "2026-09-13T21:00")
    resp = client.get("/api/weeks/2026/37", headers=headers())
    assert len(resp.json()) == 1


def test_week_invalid_week_number(client):
    assert client.get("/api/weeks/2026/0", headers=headers()).status_code == 422
    assert client.get("/api/weeks/2026/54", headers=headers()).status_code == 422


def test_week_invalid_year(client):
    assert client.get("/api/weeks/0/1", headers=headers()).status_code == 422
    assert client.get("/api/weeks/10000/1", headers=headers()).status_code == 422


def test_week_nonexistent_week_53(client):
    # 2026 has 53 ISO weeks, 2025 has 52
    assert client.get("/api/weeks/2026/53", headers=headers()).status_code == 200
    resp = client.get("/api/weeks/2025/53", headers=headers())
    assert resp.status_code == 422


def test_week_401_without_key(client):
    assert client.get("/api/weeks/2026/37").status_code == 401


def test_week_401_with_wrong_key(client):
    resp = client.get("/api/weeks/2026/37", headers=headers("nope"))
    assert resp.status_code == 401
