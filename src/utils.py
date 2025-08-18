from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_CACHE: Optional[Dict[str, Any]] = None


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    global CONFIG_CACHE
    if CONFIG_CACHE is not None:
        return CONFIG_CACHE
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        CONFIG_CACHE = yaml.safe_load(f)
    return CONFIG_CACHE


def ensure_parent_dir(file_path: str) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def format_result(rows: list[tuple] | list[dict]) -> Any:
    # If single scalar
    if isinstance(rows, list) and rows:
        first = rows[0]
        if isinstance(first, tuple) and len(first) == 1 and len(rows) == 1:
            return first[0]
        if isinstance(first, dict) and len(first) == 1 and len(rows) == 1:
            return next(iter(first.values()))
    return rows


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: str, content: str) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# Date helpers for common CXO windows
from datetime import date, timedelta


def get_last_quarter(today: Optional[date] = None) -> tuple[date, date]:
    d = today or date.today()
    quarter = (d.month - 1) // 3 + 1
    prev_q = quarter - 1 if quarter > 1 else 4
    year = d.year if quarter > 1 else d.year - 1
    start_month = 3 * (prev_q - 1) + 1
    start = date(year, start_month, 1)
    # next quarter start minus 1 day
    if prev_q == 4:
        next_start = date(year + 1, 1, 1)
    else:
        next_start = date(year, start_month + 3, 1)
    end = next_start - timedelta(days=1)
    return start, end
