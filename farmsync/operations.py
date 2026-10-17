"""Offline backup/restore with database and file integrity verification."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3

from farmsync.storage import Store


def backup(store, destination):
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError("Backup destination already exists; choose a new directory")
    target.mkdir(parents=True)
    assets_dir = target / "assets"
    assets_dir.mkdir()
    database = store.backup(target / "farmsync.sqlite3")
    manifest = {"format_version": 1, "database_sha256": sha256(database.read_bytes()).hexdigest(), "assets": []}
    # Serialize all known immutable versions, including archived evidence.
    # Opening through Store would initialize schema/WAL and mutate the snapshot
    # after computing its checksum. A backup must remain byte-for-byte immutable.
    with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        assets = db.execute("SELECT id,path,checksum FROM assets").fetchall()
    for asset in assets:
        source = Path(asset["path"])
        if not source.is_file() or sha256(source.read_bytes()).hexdigest() != asset["checksum"]:
            raise ValueError("Asset missing or modified; backup is incomplete")
        name = asset["id"] + source.suffix
        shutil.copyfile(source, assets_dir / name)
        manifest["assets"].append({"id": asset["id"], "file": name, "sha256": asset["checksum"]})
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target


def restore(source, destination):
    source, target = Path(source).resolve(), Path(destination).resolve()
    if target.exists():
        raise ValueError("Restore requires a new destination; existing service data is never overwritten")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("format_version") != 1:
        raise ValueError("Unsupported backup format")
    database = source / "farmsync.sqlite3"
    if sha256(database.read_bytes()).hexdigest() != manifest["database_sha256"]:
        raise ValueError("Database backup checksum mismatch")
    for asset in manifest["assets"]:
        name = asset["file"]
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Invalid backup asset path")
        if sha256((source / "assets" / name).read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError("Asset backup checksum mismatch")
    target.mkdir(parents=True)
    (target / "assets").mkdir()
    shutil.copyfile(database, target / "farmsync.sqlite3")
    store = Store(target / "farmsync.sqlite3")
    with store.connect() as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Restored database failed integrity check")
        for asset in manifest["assets"]:
            path = target / "assets" / asset["file"]
            shutil.copyfile(source / "assets" / asset["file"], path)
            db.execute("UPDATE assets SET path=? WHERE id=?", (str(path), asset["id"]))
        db.execute("DELETE FROM sessions")
    store.recover_interrupted()
    return store
