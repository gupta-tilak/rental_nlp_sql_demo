from __future__ import annotations
import argparse
import math
from typing import Any, Dict, List
import re

from .utils import read_json, load_config, format_result
from .db_connector import get_db
from .nlp_to_sql import NL2SQLRouter


def almost_equal(a: Any, b: Any, tol: float) -> bool:
    try:
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    except Exception:
        return False


def _parse_agent_numeric(output: str) -> Any:
    # Try to find a 'Final answer: X' pattern first
    m = re.search(r"Final answer\s*:\s*([^\n]+)", output, flags=re.IGNORECASE)
    candidate = m.group(1).strip() if m else output.strip().splitlines()[-1].strip() if output.strip().splitlines() else output
    # Extract last numeric with optional % sign
    m2 = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?%?", candidate)
    if not m2:
        return candidate
    val = m2[-1]
    is_percent = val.endswith('%')
    try:
        num = float(val.rstrip('%'))
        return num if not is_percent else num
    except Exception:
        return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file", default="data/test_queries.json")
    args = parser.parse_args()

    cfg = load_config()
    tol = cfg["answers"]["numeric_tolerance"]
    engine = cfg.get("nlp_to_sql", {}).get("engine", "rule_based")
    tests: List[Dict[str, Any]] = read_json(args.test_file)

    db = get_db()
    router = NL2SQLRouter() if engine != "agent" else None

    sql_exact, exec_correct = 0, 0

    lines: List[str] = []
    lines.append(f"# Evaluation Results (engine={engine})\n")

    for item in tests:
        qid = item.get("id")
        question = item["question"]
        gold_sql = item["gold_sql"]
        expected = item["expected_answer"]

        if engine == "agent":
            # Agent mode: run agent, parse numeric when applicable
            try:
                from .agentic import run_agentic_query  # lazy import
                agent_output = run_agentic_query(question)
            except Exception:
                agent_output = ""

            is_correct = False
            sql_match = None  # not applicable

            if isinstance(expected, (int, float)):
                pred_value = _parse_agent_numeric(str(agent_output))
                is_correct = almost_equal(pred_value, expected, tol)
            else:
                # Non-numeric structured comparisons not supported for agent in this POC
                is_correct = False

            exec_correct += 1 if is_correct else 0
            lines.append(f"- Q{qid}: exec_correct={bool(is_correct)}")
        else:
            parsed = router.to_sql(question)  # type: ignore[arg-type]
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
    if engine == "agent":
        lines.append(f"Answer Accuracy: {exec_correct}/{n} ({(exec_correct/n)*100:.1f}%)")
    else:
        lines.append(f"SQL Exact-Match Accuracy: {sql_exact}/{n} ({(sql_exact/n)*100:.1f}%)")
        lines.append(f"Execution Accuracy: {exec_correct}/{n} ({(exec_correct/n)*100:.1f}%)")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
