"""Keep test runs and quotas separate from a developer's persistent application."""
import os
from pathlib import Path
import tempfile

os.environ.setdefault("FARMSYNC_DATABASE", str(Path(tempfile.mkdtemp(prefix="farmsync-tests-")) / "test.sqlite3"))
os.environ.setdefault("FARMSYNC_ANALYSES_PER_MINUTE", "1000")
os.environ.setdefault("FARMSYNC_ANALYSES_PER_DAY", "10000")
