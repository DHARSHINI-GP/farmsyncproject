"""Durable local records, password authentication and scoped asset ownership.

SQLite is suitable for a single service instance on durable local storage. It is
not presented as a distributed multi-instance database or a managed backup service.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import pbkdf2_hmac, sha256
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid


def now():
    return datetime.now(timezone.utc).isoformat()


def password_hash(password, salt=None):
    if len(password) < 12 or len(password) > 512:
        raise ValueError("Password must contain 12–512 characters")
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000).hex()
    return f"pbkdf2_sha256$600000${salt}${digest}"


def password_matches(password, stored):
    try:
        name, iterations, salt, digest = stored.split("$")
        if name != "pbkdf2_sha256" or int(iterations) != 600_000 or len(password) > 512:
            return False
        actual = pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(actual, digest)
    except (ValueError, TypeError):
        return False


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv("FARMSYNC_DATABASE", ".runtime/farmsync.sqlite3")).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL, role TEXT NOT NULL, created TEXT NOT NULL, disabled INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
                expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL,
                original_name TEXT NOT NULL, path TEXT NOT NULL, checksum TEXT NOT NULL, metadata TEXT NOT NULL,
                created TEXT NOT NULL, deleted INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, owner TEXT NOT NULL, status TEXT NOT NULL,
                request TEXT NOT NULL, result TEXT, error TEXT, created TEXT NOT NULL, updated TEXT NOT NULL,
                cancel_requested INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT,
                owner TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, created TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                owner TEXT NOT NULL, state TEXT NOT NULL, assigned_to TEXT, resolution TEXT,
                created TEXT NOT NULL, updated TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS usage(id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,
                category TEXT NOT NULL, created REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS events_run ON events(run_id,id);
            CREATE INDEX IF NOT EXISTS usage_window ON usage(owner,category,created);
            PRAGMA user_version=1;
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_user(self, username, password, role="user"):
        if role not in {"admin", "reviewer", "user"}:
            raise ValueError("Invalid role")
        username = username.strip().casefold()
        if not 3 <= len(username) <= 128:
            raise ValueError("Username must contain 3–128 characters")
        user_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO users(id,username,password,role,created) VALUES (?,?,?,?,?)", (user_id, username, password_hash(password), role, now()))
        return {"id": user_id, "username": username, "role": role}

    def user_count(self):
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM users WHERE disabled=0").fetchone()[0]

    def admin_count(self):
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM users WHERE disabled=0 AND role='admin'").fetchone()[0]

    def login(self, username, password):
        with self.connect() as db:
            row = db.execute("SELECT * FROM users WHERE username=? AND disabled=0", (username.strip().casefold(),)).fetchone()
            # Do equal-cost password work for unknown accounts.
            stored = row["password"] if row else "pbkdf2_sha256$600000$unknown$" + "0" * 64
            if not password_matches(password, stored) or row is None:
                return None
            token = secrets.token_urlsafe(40)
            db.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?)", (sha256(token.encode()).hexdigest(), row["id"], time.time() + 8 * 3600))
            return token, {k: row[k] for k in ("id", "username", "role")}

    def principal(self, token):
        if not token or len(token) > 256:
            return None
        with self.connect() as db:
            row = db.execute("SELECT u.id,u.username,u.role FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>? AND u.disabled=0", (sha256(token.encode()).hexdigest(), time.time())).fetchone()
            return dict(row) if row else None

    def logout(self, token):
        with self.connect() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(token.encode()).hexdigest(),))

    def event(self, owner, kind, payload, run_id=None):
        with self.connect() as db:
            db.execute("INSERT INTO events(run_id,owner,kind,payload,created) VALUES (?,?,?,?,?)", (run_id, owner, kind, json.dumps(payload, default=str), now()))

    def add_asset(self, owner, kind, name, path, checksum, metadata):
        asset_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO assets(id,owner,kind,original_name,path,checksum,metadata,created) VALUES (?,?,?,?,?,?,?,?)", (asset_id, owner, kind, name, str(Path(path).resolve()), checksum, json.dumps(metadata), now()))
        return asset_id

    def asset(self, asset_id, owner, admin=False):
        with self.connect() as db:
            row = db.execute("SELECT * FROM assets WHERE id=? AND deleted=0", (asset_id,)).fetchone()
        if not row or (row["owner"] != owner and not admin):
            return None
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def assets(self, owner, kind=None):
        with self.connect() as db:
            rows = db.execute("SELECT id,kind,original_name,checksum,metadata,created FROM assets WHERE owner=? AND deleted=0 AND (? IS NULL OR kind=?) ORDER BY created DESC LIMIT 500", (owner, kind, kind)).fetchall()
        return [{**dict(r), "metadata": json.loads(r["metadata"])} for r in rows]

    def create_run(self, owner, request, status="QUEUED"):
        run_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO runs(id,owner,status,request,created,updated) VALUES (?,?,?,?,?,?)", (run_id, owner, status, json.dumps(request), now(), now()))
        self.event(owner, "QUEUED", {}, run_id)
        return run_id

    def update_run(self, run_id, status, result=None, error=None):
        with self.connect() as db:
            db.execute("UPDATE runs SET status=?,result=?,error=?,updated=? WHERE id=?", (status, json.dumps(result, default=str) if result is not None else None, error, now(), run_id))

    def run(self, run_id, owner, reviewer=False):
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        if not row or (row["owner"] != owner and not reviewer):
            return None
        return {**dict(row), "request": json.loads(row["request"]), "result": json.loads(row["result"]) if row["result"] else None}

    def runs(self, owner):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT id,status,created,updated,error FROM runs WHERE owner=? ORDER BY created DESC LIMIT 100", (owner,))]

    def events(self, run_id, owner, after=0):
        with self.connect() as db:
            rows = db.execute("SELECT id,kind,payload,created FROM events WHERE run_id=? AND owner=? AND id>? ORDER BY id LIMIT 500", (run_id, owner, after)).fetchall()
        return [{**dict(r), "payload": json.loads(r["payload"])} for r in rows]

    def cancel(self, run_id, owner):
        with self.connect() as db:
            return db.execute("UPDATE runs SET cancel_requested=1 WHERE id=? AND owner=? AND status IN ('QUEUED','RUNNING')", (run_id, owner)).rowcount > 0

    def admit(self, owner, category, limit, window=60):
        """Atomic request admission shared by threads/processes using this database."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute("SELECT COUNT(*) FROM usage WHERE owner=? AND category=? AND created>?", (owner, category, time.time() - window)).fetchone()[0]
            if count >= limit:
                return False
            db.execute("INSERT INTO usage(owner,category,created) VALUES (?,?,?)", (owner, category, time.time()))
            return True

    def create_review(self, run_id, owner):
        review_id = uuid.uuid4().hex
        with self.connect() as db:
            db.execute("INSERT INTO reviews(id,run_id,owner,state,created,updated) VALUES (?,?,?,?,?,?)", (review_id, run_id, owner, "OPEN", now(), now()))
        return review_id

    def reviews(self, owner, reviewer=False):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM reviews WHERE (?=1 OR owner=?) ORDER BY created DESC LIMIT 200", (int(reviewer), owner))]

    def resolve_review(self, review_id, reviewer, resolution):
        with self.connect() as db:
            row = db.execute("SELECT * FROM reviews WHERE id=? AND state='OPEN'", (review_id,)).fetchone()
            if not row:
                return False
            db.execute("UPDATE reviews SET state='RESOLVED',assigned_to=?,resolution=?,updated=? WHERE id=?", (reviewer, resolution, now(), review_id))
        self.event(row["owner"], "REVIEW_RESOLVED", {"review_id": review_id, "reviewer": reviewer, "resolution": resolution}, row["run_id"])
        return True

    def can_review_run(self, run_id, reviewer):
        with self.connect() as db:
            return db.execute("SELECT 1 FROM reviews WHERE run_id=? AND (assigned_to IS NULL OR assigned_to=?)", (run_id, reviewer)).fetchone() is not None

    def reviewer_asset(self, asset_id, reviewer):
        with self.connect() as db:
            rows = db.execute("SELECT r.request FROM reviews v JOIN runs r ON v.run_id=r.id WHERE v.assigned_to IS NULL OR v.assigned_to=?", (reviewer,)).fetchall()
        for row in rows:
            request = json.loads(row[0])
            if "asset:" + asset_id in {request.get("document_path"), request.get("image_filename")}:
                return self.asset(asset_id, reviewer, admin=True)
        return None

    def recover_interrupted(self):
        with self.connect() as db:
            db.execute("UPDATE runs SET status='INTERRUPTED',error='Service restarted before completion',updated=? WHERE status IN ('QUEUED','RUNNING')", (now(),))

    def backup(self, destination):
        target = Path(destination).resolve()
        if target == self.path or target.exists():
            raise ValueError("Backup destination must be a new file")
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as source:
            with sqlite3.connect(target) as output:
                source.backup(output)
                if output.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup failed integrity validation")
        return target
