#!/bin/bash
set -euo pipefail
# reset DB with fresh seed data
if [[ "${RESET_DB:-}" == "1" ]]; then
  rm -f data/rental_app.db || true
fi
uvicorn src.app:app --reload --host 127.0.0.1 --port 8000
