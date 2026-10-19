"""Relation tools: find_relations, entity_relations (§3.9–3.10).

Both build on the ``nrelations`` view (relations joined with
``named_entities`` on both sides). Paging is pushed down to SQL with the
``LIMIT n+1 OFFSET m`` trick, so large relation spaces are never fetched
whole.
"""

from __future__ import annotations

from sqlalchemy import and_, or_, select, true

from timelink.api.models.entity import Entity
from timelink.mcp.context import get_context
from timelink.mcp.errors import tool_errors as _wrapped
from timelink.mcp.paging import clamp_limit, json_safe, page_from_fetch


def _dates_conditions(date_col, dates_in: list[str] | None):
    if dates_in is None:
        return []
    if len(dates_in) != 2:
        raise ValueError(f"expected a two-element date range [after, before], got {dates_in}")
    after, before = dates_in
    conditions = []
    if after:
        conditions.append(date_col > after)
    if before:
        conditions.append(date_col < before)
    return conditions


def find_relations(
    database: str,
    relation_type: str | None = None,
    relation_value: str | None = None,
    origin_id: str | None = None,
    destination_id: str | None = None,
    origin_name: str | None = None,
    destination_name: str | None = None,
    dates_in: list[str] | None = None,
    row_limit: int = 30,
    offset: int = 0,
) -> dict:
    """Search the relation space by type, value, date and/or the parties
    involved. Population-level questions ("all kinship relations between
    1530 and 1560") live here; exploring one entity's relations is
    ``entity_relations``.

    Args:
        database: database name as shown by ``list_databases``.
        relation_type: LIKE filter, e.g. ``"kinship%"``, ``"function-in-act"``.
        relation_value: LIKE filter on the relation value.
        origin_id / destination_id: exact entity ids of the parties.
        origin_name / destination_name: LIKE filters on the parties' names.
        dates_in: ``[after, before]`` Timelink date strings (exclusive).
        row_limit: page size.
        offset: page offset for paging.
    """
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 30, ctx.settings.max_rows)

    view = db.get_view("nrelations")
    conditions = []
    if relation_type:
        conditions.append(view.c.relation_type.like(relation_type))
    if relation_value:
        conditions.append(view.c.relation_value.like(relation_value))
    if origin_id:
        conditions.append(view.c.origin_id == origin_id)
    if destination_id:
        conditions.append(view.c.destination_id == destination_id)
    if origin_name:
        conditions.append(view.c.origin_name.like(origin_name))
    if destination_name:
        conditions.append(view.c.destination_name.like(destination_name))
    conditions.extend(_dates_conditions(view.c.relation_date, dates_in))

    stmt = select(*view.c).where(and_(*conditions) if conditions else true()).limit(limit + 1).offset(offset)
    with db.session() as session:
        rows = [json_safe(dict(row)) for row in session.execute(stmt).mappings().all()]
    return page_from_fetch(rows, offset, limit)


def entity_relations(
    database: str,
    id: str,  # noqa: A002 (MCP parameter name)
    direction: str = "both",
    relation_type: str | None = None,
    row_limit: int = 50,
    offset: int = 0,
) -> dict:
    """All relations of one entity, outgoing and/or incoming, with the
    name and class of the other side. The "explore the relations of X"
    tool — chain it with ``entity_details`` to drill into counterparts.

    Args:
        database: database name as shown by ``list_databases``.
        id: the entity id.
        direction: ``out``, ``in`` or ``both`` (default).
        relation_type: optional LIKE filter, e.g. ``"kinship%"``.
        row_limit: page size.
        offset: page offset for paging.
    """
    if direction not in ("out", "in", "both"):
        raise ValueError(f"direction must be 'out', 'in' or 'both', got {direction!r}")
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 50, ctx.settings.max_rows)

    view = db.get_view("nrelations")
    side = []
    if direction in ("out", "both"):
        side.append(view.c.origin_id == id)
    if direction in ("in", "both"):
        side.append(view.c.destination_id == id)
    conditions = [or_(*side)]
    if relation_type:
        conditions.append(view.c.relation_type.like(relation_type))

    stmt = select(*view.c).where(and_(*conditions)).limit(limit + 1).offset(offset)
    with db.session() as session:
        raw = [dict(row) for row in session.execute(stmt).mappings().all()]
        classes = {}
        other_ids = {r["destination_id"] if r["origin_id"] == id else r["origin_id"] for r in raw}
        if other_ids:
            for eid, pom_class in session.execute(
                select(Entity.id, Entity.pom_class).where(Entity.id.in_(other_ids))
            ).all():
                classes[eid] = pom_class

    rows = []
    for r in raw:
        outgoing = r["origin_id"] == id
        other_id = r["destination_id"] if outgoing else r["origin_id"]
        other_name = r["destination_name"] if outgoing else r["origin_name"]
        rows.append(
            {
                "direction": "out" if outgoing else "in",
                "relation_id": r["relation_id"],
                "relation_type": r["relation_type"],
                "relation_value": r["relation_value"],
                "relation_date": r["relation_date"],
                "other_id": other_id,
                "other_name": other_name,
                "other_class": classes.get(other_id),
            }
        )
    return page_from_fetch([json_safe(row) for row in rows], offset, limit)


def register(mcp) -> None:
    """Attach this module's tools to the FastMCP server."""
    mcp.tool(
        name="find_relations",
        description=(
            "Search the relation space by type, value, date and/or the parties "
            "involved (ids or name patterns). relation_type and name filters use "
            "LIKE wildcards (e.g. kinship%, function-in-act). For exploring all "
            "relations of one entity use entity_relations instead."
        ),
    )(_wrapped(find_relations))
    mcp.tool(
        name="entity_relations",
        description=(
            "All relations of one entity (direction=out|in|both), with the name "
            "and class of the other side. Participation in acts appears as "
            "function-in-act relations; identity assertions as identification. "
            "Chain with entity_details on the other_id values."
        ),
    )(_wrapped(entity_relations))
