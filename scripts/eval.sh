#!/bin/bash
set -euo pipefail
# Reset DB from SQL before evaluation to ensure fresh test data
rm -f data/rental_app.db || true
python3 - <<'PY'
from src.db_connector import get_db
from src.utils import load_config
# Trigger DB (re)creation
cfg = load_config()
_ = get_db()
print('Database initialized at', cfg['database']['path'])
PY
python3 -m src.evaluator --test-file data/test_queries.json | tee report/accuracy_report.md
