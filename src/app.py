from __future__ import annotations
from fastapi import FastAPI
from pydantic import BaseModel

from .utils import load_config, format_result
from .db_connector import get_db
from .nlp_to_sql import NL2SQLRouter

app = FastAPI(title="Rental NLP→SQL Demo", version="0.1.0")
router = NL2SQLRouter()
config = load_config()


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query")
async def query(req: QueryRequest):
    parsed = router.to_sql(req.query)
    if not parsed.sql:
        return {"status": "fallback", "message": config["answers"]["fallback_message"]}
    db = get_db()
    try:
        rows = db.execute(parsed.sql)
        return {"status": "ok", "sql": parsed.sql, "result": format_result(rows)}
    except Exception:
        # Graceful fallback
        return {"status": "fallback", "message": config["answers"]["fallback_message"]}
