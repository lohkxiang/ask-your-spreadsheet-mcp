import csv
from decimal import Decimal
from pathlib import Path

import pytest

import server

ROWS = list(csv.DictReader((Path(__file__).parent / "sample_sales.csv").open()))


def test_describe_sheet_lists_columns():
    info = server.describe_sheet()
    assert info["rows"] == len(ROWS)
    assert set(info["number_columns"]) == {"orders", "revenue"}
    assert "Email" in info["text_columns"]["channel"]


def test_total_matches_a_hand_count():
    expected = sum(Decimal(r["revenue"]) for r in ROWS)
    assert Decimal(server.total("revenue")["total"]) == expected


def test_grouped_totals_add_up_to_the_grand_total():
    result = server.total("revenue", group_by="channel")
    assert sum(Decimal(g["total"]) for g in result["totals"]) == Decimal(result["grand_total"])


def test_month_filter():
    august = [r for r in ROWS if r["date"].startswith("2026-08")]
    result = server.total("orders", filters={"date": "2026-08"})
    assert result["rows_used"] == len(august)
    assert Decimal(result["total"]) == sum(Decimal(r["orders"]) for r in august)


def test_top_is_sorted_and_limited():
    result = server.top("product", "revenue", n=2)
    values = [Decimal(g["total"]) for g in result["totals"]]
    assert len(values) == 2 and values == sorted(values, reverse=True)


def test_unknown_column_is_refused():
    with pytest.raises(ValueError, match="Unknown column"):
        server.total("profit")


def test_text_column_cant_be_added_up():
    with pytest.raises(ValueError, match="isn't a number column"):
        server.total("channel")


@pytest.mark.anyio
async def test_tools_are_registered_read_only():
    tools = await server.mcp.list_tools()
    assert {t.name for t in tools} == {"describe_sheet", "total", "top"}
    assert all(t.annotations and t.annotations.read_only_hint for t in tools)
