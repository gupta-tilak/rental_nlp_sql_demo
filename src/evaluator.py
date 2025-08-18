from __future__ import annotations
import argparse
import math
from typing import Any, Dict, List

from .utils import read_json, write_text, load_config, format_result
from .db_connector import get_db
from .nlp_to_sql import NL2SQLRouter


def almost_equal(a: Any, b: Any, tol: float) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file", default="data/test_queries.json")
    args = parser.parse_args()

    cfg = load_config()
    tol = cfg["answers"]["numeric_tolerance"]
    tests: List[Dict[str, Any]] = read_json(args.test_file)

    db = get_db()
    router = NL2SQLRouter()

    sql_exact, exec_correct = 0, 0

    lines: List[str] = []
    lines.append("# Evaluation Results\n")

    for item in tests:
        qid = item.get("id")
        question = item["question"]
        gold_sql = item["gold_sql"]
        expected = item["expected_answer"]

        parsed = router.to_sql(question)
        pred_sql = parsed.sql
        sql_match = 1 if (pred_sql is not None and pred_sql.strip() == gold_sql.strip()) else 0
        sql_exact += sql_match

        try:
            rows = db.execute(pred_sql) if pred_sql else []
            result = format_result(rows)
            is_correct = False
            if isinstance(expected, (int, float)):
                is_correct = almost_equal(result, expected, tol)
            else:
                is_correct = result == expected
            exec_correct += 1 if is_correct else 0
        except Exception:
            pass

        lines.append(f"- Q{qid}: SQL exact match={bool(sql_match)}; exec_correct={bool(is_correct)}")

    n = len(tests)
    lines.append("")
    lines.append(f"SQL Exact-Match Accuracy: {sql_exact}/{n} ({(sql_exact/n)*100:.1f}%)")
    lines.append(f"Execution Accuracy: {exec_correct}/{n} ({(exec_correct/n)*100:.1f}%)")

    write_text("report/accuracy_report.md", "\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
