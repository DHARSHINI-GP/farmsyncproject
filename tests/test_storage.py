import json
import sqlite3

import pytest

from farmsync.storage import Store, password_hash, password_matches


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "records.sqlite3")


def test_passwords_and_sessions_are_not_stored_in_plaintext(store):
    user = store.create_user("Alice", "a-long-test-password")
    token, principal = store.login("alice", "a-long-test-password")
    assert principal["id"] == user["id"]
    assert store.login("alice", "wrong-password") is None
    assert store.principal(token)["username"] == "alice"
    with store.connect() as db:
        row = db.execute("SELECT password FROM users").fetchone()
        assert row[0] != "a-long-test-password"
        assert db.execute("SELECT token_hash FROM sessions").fetchone()[0] != token
    store.logout(token)
    assert store.principal(token) is None


def test_owned_assets_are_isolated_and_persist_after_reopen(store, tmp_path):
    asset_id = store.add_asset("alice", "pdf", "same.pdf", tmp_path / "file.pdf", "abc", {})
    assert store.asset(asset_id, "bob") is None
    assert Store(store.path).asset(asset_id, "alice")["original_name"] == "same.pdf"


def test_admission_is_enforced_across_connections(store):
    assert store.admit("alice", "analysis", 1)
    assert not Store(store.path).admit("alice", "analysis", 1)
    assert store.admit("bob", "analysis", 1)


def test_run_review_events_and_restart_recovery(store):
    run_id = store.create_run("alice", {"query": "inspect"})
    assert store.run(run_id, "bob") is None
    store.update_run(run_id, "RUNNING")
    Store(store.path).recover_interrupted()
    assert store.run(run_id, "alice")["status"] == "INTERRUPTED"
    review = store.create_review(run_id, "alice")
    assert not store.reviews("bob")
    assert store.resolve_review(review, "reviewer", "Source must be checked")
    assert not store.resolve_review(review, "reviewer", "Second resolution")
    assert store.events(run_id, "alice")[-1]["kind"] == "REVIEW_RESOLVED"


def test_backup_is_consistent_and_restore_is_verifiable(store, tmp_path):
    run_id = store.create_run("alice", {"query": "immutable evidence"})
    path = store.backup(tmp_path / "backup.sqlite3")
    restored = Store(path)
    assert restored.run(run_id, "alice")["request"]["query"] == "immutable evidence"
    with pytest.raises(ValueError):
        store.backup(path)
