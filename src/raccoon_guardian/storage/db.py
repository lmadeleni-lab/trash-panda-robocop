from __future__ import annotations

import sqlite3
from pathlib import Path

from raccoon_guardian.storage.migrations import SCHEMA_VERSION, schema_statements


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        for statement in schema_statements():
            connection.execute(statement)
        current = connection.execute("SELECT COUNT(*) FROM schema_version").fetchone()
        assert current is not None
        if current[0] == 0:
            connection.execute("INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,))
        connection.commit()
