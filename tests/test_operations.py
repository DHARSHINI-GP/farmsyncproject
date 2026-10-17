from hashlib import sha256
import pytest
from farmsync.storage import Store
from farmsync.operations import backup, restore


def test_full_backup_restore_includes_files_and_revokes_sessions(tmp_path):
    store=Store(tmp_path / "original/app.sqlite3")
    user=store.create_user("alice", "a-long-secret-password")
    token,_=store.login("alice", "a-long-secret-password")
    file=tmp_path / "source.pdf"
    file.write_bytes(b"immutable test evidence")
    asset=store.add_asset(user["id"], "pdf", "source.pdf", file, sha256(file.read_bytes()).hexdigest(), {})
    destination=backup(store, tmp_path / "backup")
    recovered=restore(destination, tmp_path / "restored")
    owned=recovered.asset(asset,user["id"])
    assert owned and recovered.principal(token) is None
    from pathlib import Path
    assert Path(owned["path"]).read_bytes() == file.read_bytes()
    assert recovered.login("alice", "a-long-secret-password") is not None
    with pytest.raises(ValueError):
        restore(destination,tmp_path / "restored")


def test_corrupt_backup_is_rejected_before_restore_target_creation(tmp_path):
    store=Store(tmp_path / "app.sqlite3")
    source=backup(store,tmp_path / "backup")
    (source / "farmsync.sqlite3").write_bytes(b"modified")
    with pytest.raises(ValueError,match="checksum"):
        restore(source,tmp_path / "restored")
    assert not (tmp_path / "restored").exists()
