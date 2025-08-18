#!/bin/bash
set -euo pipefail
uvicorn src.app:app --reload --host 127.0.0.1 --port 8000
