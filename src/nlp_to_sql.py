from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

from .utils import get_last_quarter
from .utils import load_config


@dataclass
class NL2SQLResult:
    sql: Optional[str]
    reason: Optional[str] = None


class RuleBasedNL2SQL:
    def __init__(self) -> None:
        pass

    def _extract_city(self, text: str) -> Optional[str]:
        # capture following the word 'in', then strip trailing time phrases
        m = re.search(r"\bin\s+([A-Za-z\-\s]+)", text)
        if not m:
            return None
        candidate = m.group(1).strip()
        # remove common trailing time phrases if present
        for stopper in [
            " last quarter",
            " this quarter",
            " next quarter",
            " this year",
            " last year",
            " this month",
            " last month",
            " today",
        ]:
            if candidate.endswith(stopper):
                candidate = candidate[: -len(stopper)].strip()
        if not candidate:
            return None
        return " ".join(w.capitalize() for w in candidate.split())

    def _is_last_quarter(self, text: str) -> bool:
        return "last quarter" in text.lower()

    def parse(self, question: str) -> NL2SQLResult:
        q = question.strip()
        low = q.lower()

        # Occupancy rate in <city> last quarter
        if "occupancy" in low and ("rate" in low or "percentage" in low):
            city = self._extract_city(low) or ""
            if self._is_last_quarter(low):
                start, end = get_last_quarter()
                sql = (
                    "SELECT ROUND(100.0 * COUNT(DISTINCT b.property_id) / NULLIF(COUNT(DISTINCT p.property_id),0), 2) AS occupancy_rate "
                    "FROM properties p LEFT JOIN bookings b ON p.property_id = b.property_id "
                    f"WHERE p.city='{city}' AND b.start_date >= '{start.isoformat()}' AND b.end_date <= '{end.isoformat()}';"
                )
                return NL2SQLResult(sql=sql)

        # Top 10 tenants by rent paid
        if ("top" in low and "tenant" in low) or ("rent paid" in low and "tenant" in low):
            sql = (
                "SELECT u.first_name, u.last_name, SUM(pay.amount) AS total_paid "
                "FROM payments pay JOIN users u ON u.user_id = pay.tenant_id "
                "WHERE pay.status='successful' GROUP BY u.user_id ORDER BY total_paid DESC LIMIT 10;"
            )
            return NL2SQLResult(sql=sql)

        # Avg rating of apartments vs houses
        if ("avg" in low or "average" in low) and "rating" in low and ("apartment" in low or "house" in low):
            sql = (
                "SELECT p.property_type, ROUND(AVG(r.rating),2) AS avg_rating "
                "FROM reviews r JOIN properties p ON r.property_id = p.property_id "
                "WHERE p.property_type IN ('apartment','house') GROUP BY p.property_type;"
            )
            return NL2SQLResult(sql=sql)

        # Landlords with most revenue this year
        if "landlord" in low and ("revenue" in low or "income" in low):
            sql = (
                "SELECT u.first_name, u.last_name, SUM(pay.amount) AS total_revenue "
                "FROM payments pay JOIN bookings b ON pay.booking_id=b.booking_id JOIN properties p ON b.property_id=p.property_id JOIN users u ON u.user_id=p.landlord_id "
                "WHERE pay.status='successful' AND strftime('%Y', pay.payment_date) = '2025' GROUP BY u.user_id ORDER BY total_revenue DESC;"
            )
            return NL2SQLResult(sql=sql)

        # Available 2BHKs under $2500 in London
        if ("available" in low) and ("bhk" in low or "bed" in low or "bedroom" in low) and ("under" in low or "<" in low):
            # Rough parse: e.g., "2bhk", "2 bhk", "2-bed", "2 bedroom"
            m = re.search(r"(\d+)\s*(bhk|bed|bedroom)", low)
            bedrooms = m.group(1) if m else "2"
            mprice = re.search(r"under\s*\$?(\d+)|<\s*\$?(\d+)", low)
            price = (mprice.group(1) or mprice.group(2)) if mprice else "2500"
            city = self._extract_city(low) or "London"
            sql = (
                "SELECT title, address, rent_price FROM properties "
                f"WHERE city='{city}' AND bedrooms={bedrooms} AND rent_price < {price} AND status='available';"
            )
            return NL2SQLResult(sql=sql)

        return NL2SQLResult(sql=None, reason="unsupported_intent")


class HFNL2SQL:
    def __init__(self, model_name: str) -> None:
        from transformers import pipeline  # type: ignore
        self.pipe = pipeline(
            "text2text-generation",
            model=model_name,
        )

    def parse(self, question: str) -> NL2SQLResult:
        # Build live schema string from the configured DB
        from .utils import load_config
        from sqlalchemy import create_engine, inspect  # type: ignore
        cfg = load_config()
        db_path = cfg["database"]["path"]
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        parts: list[str] = []
        for t in tables:
            cols = ", ".join([c["name"] for c in inspector.get_columns(t)])
            parts.append(f"{t}({cols})")
        schema_str = "; ".join(parts)
        prompt = (
            "You are an expert text-to-SQL translator for a SQLite database. "
            "Use only the provided schema. Write a single valid SQLite SQL query ending with a semicolon.\n"
            f"Schema: {schema_str}.\n"
            "Guidelines: Dates are ISO text (YYYY-MM-DD). SQLite lacks INTERVAL. Use strftime('%Y', col) for year.\n"
            "Question: " + question
        )
        out = self.pipe(prompt, max_new_tokens=128)
        text = out[0]["generated_text"].strip()
        if not text.endswith(";"):
            text += ";"
        return NL2SQLResult(sql=text)


class NL2SQLRouter:
    def __init__(self) -> None:
        cfg = load_config()
        engine = cfg.get("nlp_to_sql", {}).get("engine", "rule_based")
        if engine == "hf":
            self.engine = HFNL2SQL(cfg["nlp_to_sql"]["hf_model"])  # type: ignore
        else:
            self.engine = RuleBasedNL2SQL()

    def to_sql(self, question: str) -> NL2SQLResult:
        return self.engine.parse(question)
