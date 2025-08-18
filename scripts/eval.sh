#!/bin/bash
set -euo pipefail
python3 -m src.evaluator --test-file data/test_queries.json | tee report/accuracy_report.md
