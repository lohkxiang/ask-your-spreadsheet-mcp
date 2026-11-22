"""Ask your spreadsheet: a small, read-only MCP server.

It lets an AI assistant answer questions about a sales spreadsheet (a CSV file)
in plain English. The assistant decides what to look up; this code does the
maths. Nothing here can change or delete the file.

Run it:  python server.py
Point it at your own file:  SHEET_PATH=/path/to/sales.csv python server.py
"""

from __future__ import annotations

import csv
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

SHEET_PATH = Path(os.environ.get("SHEET_PATH", Path(__file__).parent / "sample_sales.csv"))
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True)

mcp = MCPServer(
    name="ask-your-spreadsheet",
    instructions=(
        "Answers questions about one sales spreadsheet. Call describe_sheet first to see "
        "the columns. Use total and top for any figure: never add numbers up yourself."
    ),
)


def _load() -> list[dict[str, str]]:
    """Read the whole sheet fresh on every call, so answers match the file as it is now."""
    with SHEET_PATH.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _number(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", "").replace("£", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def _numeric_columns(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    return [c for c in rows[0] if all(_number(r[c]) is not None for r in rows if r[c] != "")]


def _check_column(rows: list[dict[str, str]], column: str) -> None:
    if rows and column not in rows[0]:
        raise ValueError(f"Unknown column '{column}'. Columns are: {', '.join(rows[0])}.")


def _filter(rows: list[dict[str, str]], filters: dict[str, str] | None) -> list[dict[str, str]]:
    """Keep rows where each column equals the given value. A date column also matches a
    'YYYY-MM' prefix, so {'date': '2026-08'} means August 2026."""
    for column, value in (filters or {}).items():
        _check_column(rows, column)
        rows = [r for r in rows if r[column] == value or r[column].startswith(value)]
    return rows


@mcp.tool(annotations=READ_ONLY)
def describe_sheet() -> dict:
    """See what's in the spreadsheet: its columns, which ones hold numbers, how many rows
    there are, and the distinct values of each text column. Call this first."""
    rows = _load()
    numeric = _numeric_columns(rows)
    text_values = {
        c: sorted({r[c] for r in rows})[:25] for c in (rows[0] if rows else []) if c not in numeric
    }
    return {"rows": len(rows), "number_columns": numeric, "text_columns": text_values}


@mcp.tool(annotations=READ_ONLY)
def total(measure: str, group_by: str | None = None, filters: dict[str, str] | None = None) -> dict:
    """Add up a number column (e.g. revenue or orders), exactly.

    measure: the number column to add up.
    group_by: optional text column to split the total by (e.g. channel).
    filters: optional {column: value} to narrow the rows first, e.g.
             {"region": "London"} or {"date": "2026-08"} for one month.
    """
    rows = _load()
    _check_column(rows, measure)
    if measure not in _numeric_columns(rows):
        raise ValueError(f"'{measure}' isn't a number column.")
    rows = _filter(rows, filters)
    if group_by is None:
        return {"measure": measure, "rows_used": len(rows), "total": str(sum(_number(r[measure]) or 0 for r in rows))}
    _check_column(rows, group_by)
    groups: dict[str, Decimal] = {}
    for r in rows:
        groups[r[group_by]] = groups.get(r[group_by], Decimal(0)) + (_number(r[measure]) or 0)
    ordered = sorted(groups.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "measure": measure,
        "group_by": group_by,
        "rows_used": len(rows),
        "totals": [{group_by: k, "total": str(v)} for k, v in ordered],
        "grand_total": str(sum(groups.values(), Decimal(0))),
    }


@mcp.tool(annotations=READ_ONLY)
def top(group_by: str, measure: str, n: int = 5, filters: dict[str, str] | None = None) -> dict:
    """Rank the values of a text column by a number column, highest first.
    Example: the top 3 products by revenue in London."""
    result = total(measure, group_by, filters)
    return {**result, "totals": result["totals"][: max(1, min(n, 25))]}


if __name__ == "__main__":
    mcp.run()
