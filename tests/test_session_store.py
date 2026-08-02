from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.storage.session_store import SessionStore


def test_save_list_and_delete(tmp_path):
    store = SessionStore(tmp_path)
    payload = {
        "id": "abc123",
        "status": "completed",
        "created_at": datetime.now(UTC).isoformat(),
    }
    path = store.save(payload)
    assert path.exists()
    assert store.list_sessions()[0]["id"] == "abc123"
    assert store.delete("abc123") is True
    assert store.list_sessions() == []


def test_purge_older_than(tmp_path):
    store = SessionStore(tmp_path)
    old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    fresh = datetime.now(UTC).isoformat()
    store.save({"id": "old", "status": "completed", "created_at": old, "ended_at": old})
    store.save({"id": "fresh", "status": "completed", "created_at": fresh, "ended_at": fresh})
    assert store.purge_older_than(30) == 1
    assert [item["id"] for item in store.list_sessions()] == ["fresh"]
