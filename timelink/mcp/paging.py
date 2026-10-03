"""Row limits, paging and JSON-safe serialization shared by all tools.

Conventions (``docs/mcp-tools-draft.md`` §2): every tabular tool takes
``row_limit`` (default per tool) and ``offset`` (default 0), and returns
``{rows, row_count, truncated, next_offset}`` — ``next_offset`` is present
when more rows exist. The per-page hard cap comes from
``TIMELINK_MCP_MAX_ROWS``.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any

import pandas as pd


def clamp_limit(row_limit: int | None, default: int, max_rows: int) -> int:
    """Clamp a requested page size to ``[1, max_rows]``, using ``default``."""
    limit = default if row_limit is None else int(row_limit)
    return max(1, min(limit, max_rows))


def json_safe(value: Any) -> Any:
    """Convert a value to something JSON-serializable (dates → ISO, NaN → None)."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(v) for v in value]
    return str(value)


def df_records(df: pd.DataFrame | None) -> list[dict]:
    """Serialize a library DataFrame to JSON-safe record dicts.

    A named index (e.g. the entity id) becomes a column; ``NaN``/``NaT``
    become None.
    """
    if df is None or len(df) == 0:
        return []
    if df.index.name is not None:
        df = df.reset_index()
    # round-trip through pandas' JSON writer: handles numpy types, NaN and
    # timestamps in one go
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _page(rows: list[dict], offset: int, limit: int, total: int | None) -> dict:
    truncated = offset + len(rows) < total if total is not None else False
    result = {
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
    }
    if total is not None:
        result["total_count"] = total
    if truncated:
        result["next_offset"] = offset + limit
    return result


def page_slice(rows: list[dict], offset: int, limit: int, total: int | None = None) -> dict:
    """Page an in-memory result list (used when the library returns everything)."""
    if total is None:
        total = len(rows)
    return _page(rows[offset : offset + limit], offset, limit, total)


def page_from_fetch(rows: list[dict], offset: int, limit: int) -> dict:
    """Page a fetch that used the ``LIMIT limit+1 OFFSET offset`` trick.

    ``rows`` holds at most ``limit + 1`` rows; the extra row only signals
    that more rows exist and is dropped from the page. No ``total_count``
    is reported — the database was never asked to count.
    """
    truncated = len(rows) > limit
    page = rows[:limit]
    result = {"rows": page, "row_count": len(page), "truncated": truncated}
    if truncated:
        result["next_offset"] = offset + limit
    return result


def empty_page() -> dict:
    """The standard response shape for a query with no results."""
    return {"rows": [], "row_count": 0, "truncated": False, "total_count": 0}
