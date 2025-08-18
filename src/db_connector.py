from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Iterable, List, Tuple

from .utils import load_config, ensure_parent_dir


class Database:
    def __init__(self, db_path: str, init_sql_path: str | None = None) -> None:
        self.db_path = db_path
        self.init_sql_path = init_sql_path
        ensure_parent_dir(db_path)
        self._maybe_init()

    def _maybe_init(self) -> None:
        if not Path(self.db_path).exists() and self.init_sql_path:
            self._initialize_from_sql(self.init_sql_path)

    def _initialize_from_sql(self, sql_path: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            conn.executescript(sql_script)
            conn.commit()

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> List[Tuple[Any, ...]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql, params or [])
            rows = cursor.fetchall()
            return [tuple(row) for row in rows]


_db_singleton: Database | None = None


def get_db() -> Database:
    global _db_singleton
    if _db_singleton is None:
        cfg = load_config()
        _db_singleton = Database(
            db_path=cfg["database"]["path"],
            init_sql_path=cfg["database"].get("init_sql"),
        )
    return _db_singleton
