from __future__ import annotations
from typing import Optional, Any
from pathlib import Path
import sqlite3
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
    init_sql = cfg["database"].get("init_sql")

    # Ensure DB directory exists and initialize from SQL if missing
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if not Path(db_path).exists() and init_sql:
        with sqlite3.connect(db_path) as conn:
            with open(init_sql, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            conn.commit()

    engine_uri = f"sqlite:///{db_path}"
    engine = create_engine(engine_uri)

    # Build dynamic tool description from live DB schema
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    schema_description = (
        "You can query the SQLite database. Important guidelines for this schema and SQLite: \n"
        "- Always inspect all relevant tables and their relationships before writing SQL.\n"
        "- For multi-table queries, use explicit JOINs and qualify column names with table aliases.\n"
        "- City information is stored in table 'properties' as column 'city'. To filter by city in 'bookings' or 'payments', JOIN via properties: \n"
        "    bookings b JOIN properties p ON b.property_id = p.property_id\n"
        "    payments pay JOIN bookings b ON pay.booking_id = b.booking_id JOIN properties p ON b.property_id = p.property_id\n"
        "- For tenant or landlord info, JOIN users u ON u.user_id = ... (tenant_id or landlord_id).\n"
        "- Example: Top tenants by rent paid: \n"
        "    SELECT u.first_name, u.last_name, SUM(pay.amount) as total_rent\n"
        "    FROM payments pay JOIN bookings b ON pay.booking_id = b.booking_id\n"
        "    JOIN users u ON b.tenant_id = u.user_id\n"
        "    GROUP BY u.user_id ORDER BY total_rent DESC LIMIT 10;\n"
        "- Example: Occupancy rate in a city last quarter: \n"
        "    SELECT 100.0 * COUNT(DISTINCT b.property_id) / NULLIF(COUNT(DISTINCT p.property_id), 0)\n"
        "    FROM bookings b JOIN properties p ON b.property_id = p.property_id\n"
        "    WHERE p.city = 'CITY' AND b.start_date >= ? AND b.end_date <= ?\n"
        "- SQLite does NOT support 'INTERVAL' syntax. Use ISO dates like 'YYYY-MM-DD' directly in comparisons.\n"
        "- Dates are stored as ISO text (YYYY-MM-DD) in this DB. Compare as strings or use strftime where needed.\n"
        "- Year extraction uses strftime('%Y', date_column). Example: strftime('%Y', pay.payment_date) = '2025'.\n"
        "- For last quarter dates, call get_last_quarter() and pass its return value directly as the params list for '?' placeholders (e.g., sql_select(\"... >= ? AND ... <= ?\", get_last_quarter())).\n"
        "- Always write correct SQL for SQLite.\n"
        "- Prefer returning final numeric answers directly using sql_scalar to avoid brittle parsing.\n"
        "- Parametrization: sql_scalar and sql_select accept an optional second argument 'params' as a list/tuple/JSON list for '?' placeholders. Example: sql_scalar(\"SELECT ... WHERE x >= ? AND y <= ?\", [d1, d2]).\n"
        "- If a column name is ambiguous, always qualify it with the table alias.\n"
        "- For best performance, use GROUP BY and ORDER BY only when needed.\n"
        "- Available tables, columns, and foreign keys:"
    )
    for table in table_names:
        columns_info = [(col["name"], str(col["type"])) for col in inspector.get_columns(table)]
        fks = inspector.get_foreign_keys(table)
        fk_lines = []
        for fk in fks:
            referred_table = fk.get("referred_table")
            con_cols = fk.get("constrained_columns") or []
            ref_cols = fk.get("referred_columns") or []
            if referred_table and con_cols and ref_cols:
                pairs = ", ".join([f"{c} -> {referred_table}.{r}" for c, r in zip(con_cols, ref_cols)])
                fk_lines.append(f"  - {pairs}")
        table_desc = f"\n\nTable '{table}':\nColumns:\n" + "\n".join([f"  - {name}: {ctype}" for name, ctype in columns_info])
        if fk_lines:
            table_desc += "\nForeign Keys:\n" + "\n".join(fk_lines)
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
        # Return a JSON array so it can be directly used as params for '?' placeholders
        # in sql_select/sql_scalar without needing extra parsing/imports.
        return json.dumps([start.isoformat(), end.isoformat()])

    # Attach helpful descriptions to tools
    sql_select.description = (
        schema_description
        + "\n\nTip: To filter by city for bookings: JOIN properties p ON p.property_id = b.property_id and use p.city."
    )
    sql_scalar.description = (
        schema_description
        + "\n\nUse this when you need a single number (COUNT, SUM, AVG, etc.). "
        "Example occupancy rate pattern: \n"
        "1) Use get_last_quarter() to get dates d1,d2.\n"
        "2) Compute numerator = COUNT(DISTINCT b.property_id) from bookings b JOIN properties p ON b.property_id=p.property_id WHERE p.city='CITY' AND b.start_date>=d1 AND b.end_date<=d2.\n"
        "3) Compute denominator = COUNT(DISTINCT p.property_id) from properties p WHERE p.city='CITY'.\n"
        "4) Compute 100.0 * numerator / NULLIF(denominator,0)."
    )
    get_last_quarter.description = (
        "Get last quarter date boundaries as a JSON array [start_date, end_date]. Use it directly as params."
    )

    model = InferenceClientModel(model_id=model_id)
    agent = CodeAgent(tools=[sql_select, sql_scalar, get_last_quarter], model=model)
    return agent


def run_agentic_query(question: str, model_id: Optional[str] = None) -> str:
    agent = build_agent(model_id=model_id)
    return agent.run(question)
