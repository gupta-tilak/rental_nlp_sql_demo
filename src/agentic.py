from __future__ import annotations
from typing import Optional, Any
import json

from .utils import load_config, get_last_quarter as compute_last_quarter


def build_agent(model_id: Optional[str] = None):
    # Lazy imports to avoid pulling heavy deps during normal import/tests
    from dotenv import load_dotenv  # type: ignore
    from sqlalchemy import create_engine, inspect  # type: ignore
    from smolagents import tool, CodeAgent, InferenceClientModel  # type: ignore

    load_dotenv()
    cfg = load_config()
    model_id = model_id or cfg["nlp_to_sql"].get("agent_model_id", "meta-llama/Llama-3.1-8B-Instruct")

    db_path = cfg["database"]["path"]
    engine_uri = f"sqlite:///{db_path}"
    engine = create_engine(engine_uri)

    # Build dynamic tool description from live DB schema
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    schema_description = (
        "You can query the SQLite database. Important guidelines for this schema and SQLite: \n"
        "- City information is stored in table 'properties' as column 'city'. If you need to filter by city while working with 'bookings' or 'payments', JOIN via properties: \n"
        "  bookings b JOIN properties p ON b.property_id = p.property_id.\n"
        "- SQLite does NOT support 'INTERVAL' syntax. Use ISO dates like 'YYYY-MM-DD' directly in comparisons.\n"
        "- Year extraction uses strftime('%Y', date_column). Example: strftime('%Y', pay.payment_date) = '2025'.\n"
        "- For last quarter dates, call the provided tool get_last_quarter() and use the returned start/end dates (do NOT call it inside SQL).\n"
        "- Always write correct SQL for SQLite.\n"
        "- Prefer returning final numeric answers directly using sql_scalar to avoid brittle parsing.\n"
        "- Parametrization: sql_scalar and sql_select accept an optional second argument 'params' as a list/tuple/JSON list for '?' placeholders. Example: sql_scalar(\"SELECT ... WHERE x >= ? AND y <= ?\", [d1, d2]).\n"
        "Available tables and columns:"
    )
    for table in table_names:
        columns_info = [(col["name"], str(col["type"])) for col in inspector.get_columns(table)]
        table_desc = f"\n\nTable '{table}':\nColumns:\n" + "\n".join([f"  - {name}: {ctype}" for name, ctype in columns_info])
        schema_description += table_desc

    @tool
    def sql_select(query: str, params: Any | None = None) -> str:
        """
        Execute a SQL SELECT query and return JSON with rows as a list of objects (column->value). Use this for multi-row results.

        Args:
            query: A valid SQLite SELECT query.
            params: Optional parameters for '?' placeholders. Provide as list/tuple or JSON-encoded list.
        Returns:
            A JSON string like {"rows": [{"col": value, ...}, ...]}.
        """
        bind: tuple | None = None
        if params is not None:
            if isinstance(params, (list, tuple)):
                bind = tuple(params)
            elif isinstance(params, str):
                try:
                    parsed = json.loads(params)
                    if isinstance(parsed, list):
                        bind = tuple(parsed)
                    else:
                        bind = (params,)
                except Exception:
                    bind = (params,)
        else:
            bind = tuple()
        with engine.connect() as con:
            result = con.exec_driver_sql(query, bind)
            cols = result.keys()
            rows = [dict(zip(cols, row)) for row in result.fetchall()]
        return json.dumps({"rows": rows})

    @tool
    def sql_scalar(query: str, params: Any | None = None) -> str:
        """
        Execute a SQL SELECT that returns a single scalar (e.g., COUNT(*), SUM(...)). Returns the scalar as string.

        Args:
            query: A valid SQLite SELECT returning exactly one value and one row.
            params: Optional parameters for '?' placeholders. Provide as list/tuple or JSON-encoded list.
        Returns:
            The scalar value as a string.
        """
        bind: tuple | None = None
        if params is not None:
            if isinstance(params, (list, tuple)):
                bind = tuple(params)
            elif isinstance(params, str):
                try:
                    parsed = json.loads(params)
                    if isinstance(parsed, list):
                        bind = tuple(parsed)
                    else:
                        bind = (params,)
                except Exception:
                    bind = (params,)
        else:
            bind = tuple()
        with engine.connect() as con:
            result = con.exec_driver_sql(query, bind)
            row = result.fetchone()
            if row is None or len(row) == 0:
                return ""
            return str(row[0])

    @tool
    def get_last_quarter() -> str:
        """
        Returns last quarter start and end dates as JSON with fields start_date and end_date, ISO formatted YYYY-MM-DD.
        Use these dates for filtering ranges in SQLite.
        """
        start, end = compute_last_quarter()
        return json.dumps({"start_date": start.isoformat(), "end_date": end.isoformat()})

    # Attach helpful descriptions to tools
    sql_select.description = (
        schema_description
        + "\n\nTip: To filter by city for bookings: JOIN properties p ON p.property_id = b.property_id and use p.city."
    )
    sql_scalar.description = (
        "Use this when you need a single number (COUNT, SUM, AVG, etc.). "
        "Example occupancy rate pattern: \n"
        "1) Use get_last_quarter() to get dates d1,d2.\n"
        "2) Compute numerator = COUNT(DISTINCT b.property_id) from bookings b JOIN properties p ON b.property_id=p.property_id WHERE p.city='CITY' AND b.start_date>=d1 AND b.end_date<=d2.\n"
        "3) Compute denominator = COUNT(DISTINCT p.property_id) from properties p WHERE p.city='CITY'.\n"
        "4) Compute 100.0 * numerator / NULLIF(denominator,0)."
    )
    get_last_quarter.description = "Get last quarter date boundaries as JSON."

    model = InferenceClientModel(model_id=model_id)
    agent = CodeAgent(tools=[sql_select, sql_scalar, get_last_quarter], model=model)
    return agent


def run_agentic_query(question: str, model_id: Optional[str] = None) -> str:
    agent = build_agent(model_id=model_id)
    return agent.run(question)
