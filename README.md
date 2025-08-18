### Rental NLP → SQL Demo (Hackathon POC)

A fast, local Proof-of-Concept that converts natural language questions into SQL over a rental marketplace schema and returns answers via a simple API.

- Language: Python 3.10+
- Framework: FastAPI
- Database: SQLite (auto-initialized from `data/rental_app.sql`)
- NL→SQL: Rule-based templates, optional HuggingFace fallback, or Agentic LLM via smolagents

---

## Quickstart

1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Configure (optional)

- See `config.yaml`. Defaults are sensible. You can switch the NL→SQL engine to a HuggingFace text-generation model by setting `nlp_to_sql.engine: hf`. This is optional and not required for the demo to run.

4) Initialize the DB (auto)

- On first run, the app will create `data/rental_app.db` by executing `data/rental_app.sql`.

5) Run the API server

```bash
uvicorn src.app:app --reload
```

- Swagger UI: `http://127.0.0.1:8000/docs`

---

## API

- `GET /health` → health check
- `POST /query` → body `{ "query": "Your natural language question" }`
  - Response:
    - On success (rule_based/hf): `{ "sql": "...", "result": <number|list>, "status": "ok" }`
    - On success (agent): `{ "agent_output": "...", "status": "ok" }`
    - On fallback: `{ "message": "Sorry, unable to answer at this point in time.", "status": "fallback" }`

Example

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the occupancy rate of properties in Bradford last quarter?"}'
```

---

## Evaluation

Evaluate against `data/test_queries.json`:

```bash
python -m src.evaluator --test-file data/test_queries.json
```

This computes:
- SQL exact-match accuracy
- Execution accuracy (numeric scalar answers with tolerance)
- Writes a brief report to `report/accuracy_report.md`

---

## Repo Layout

- `README.md` — setup & usage
- `requirements.txt` — dependencies
- `config.yaml` — configuration (DB path, engine)
- `data/`
  - `rental_app.sql` — schema + seed data
  - `test_queries.json` — evaluation queries
- `src/`
  - `app.py` — FastAPI app
  - `nlp_to_sql.py` — NL→SQL engines (rule-based + HF optional)
  - `db_connector.py` — SQLite initialization and query execution
  - `evaluator.py` — evaluation CLI
  - `utils.py` — helpers (config, formatting, date windows)
- `notebooks/`
  - `exploratory.ipynb` — scratchpad
- `report/`
  - `accuracy_report.md` — generated/maintained results
- `tests/`
  - `test_app.py` — endpoint tests
  - `test_nlp_to_sql.py` — NL→SQL tests

---

## Notes

- Modes:
  - `rule_based`: deterministic templates for demo queries (default)
  - `hf`: direct text-to-SQL using a small HF model
  - `agent`: agentic SQL via smolagents with schema-aware tool and iterative refinement
- Configure in `config.yaml` under `nlp_to_sql.engine`.
- For complex or unsupported questions, the system answers gracefully with: "Sorry, unable to answer at this point in time."

---

## License

MIT
