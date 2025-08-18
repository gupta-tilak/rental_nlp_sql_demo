from __future__ import annotations
from src.nlp_to_sql import NL2SQLRouter


def test_rule_based_examples():
    router = NL2SQLRouter()

    q1 = "What’s the occupancy rate of properties in Bradford last quarter?"
    assert router.to_sql(q1).sql is not None

    q2 = "Top 10 tenants by rent paid"
    assert router.to_sql(q2).sql is not None

    q3 = "Avg rating of apartments vs houses"
    assert router.to_sql(q3).sql is not None

    q4 = "Landlords with most revenue this year"
    assert router.to_sql(q4).sql is not None

    q5 = "Available 2BHKs under $2500 in London"
    assert router.to_sql(q5).sql is not None
