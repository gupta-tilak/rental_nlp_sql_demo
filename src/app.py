from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .utils import load_config, format_result
from .db_connector import get_db
from .nlp_to_sql import NL2SQLRouter
from .agentic import run_agentic_query

app = FastAPI(title="Rental NLP→SQL Demo", version="0.1.0")
router = NL2SQLRouter()
config = load_config()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
async def health():
    return {"status": "ok"}
@app.get("/")
async def index(request: Request):
    engine = config.get("nlp_to_sql", {}).get("engine", "rule_based")
    return templates.TemplateResponse("index.html", {"request": request, "engine": engine})



@app.post("/query")
async def query(req: QueryRequest):
    engine = config.get("nlp_to_sql", {}).get("engine", "rule_based")
    if engine == "agent":
        try:
            output = run_agentic_query(req.query)
            return {"status": "ok", "agent_output": output}
        except Exception:
            return {"status": "fallback", "message": config["answers"]["fallback_message"]}

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
