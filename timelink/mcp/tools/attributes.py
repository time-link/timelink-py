"""Search-by-attribute tools (§3.4–3.8).

Thin wrappers over ``timelink.pandas``; results are paged record lists
(see :mod:`timelink.mcp.paging`). Dates are Timelink date strings
(``yyyy``, ``yyyymm`` or ``yyyymmdd``) compared lexically; string filters
use SQL LIKE semantics (``%`` any string, ``_`` one char), lists mean
exact IN-match.
"""

from __future__ import annotations

from timelink.api.models.entity import Entity
from timelink.mcp.context import get_context
from timelink.mcp.errors import tool_errors as _wrapped
from timelink.mcp.paging import clamp_limit, df_records, empty_page, page_slice
from timelink.pandas.attribute_values import attribute_values as attribute_values_df
from timelink.pandas.entities_with_attribute import entities_with_attribute
from timelink.pandas.group_attributes import group_attributes
from timelink.pandas.name_to_df import pname_to_df


def _tuple_or_none(pair: list[str] | None) -> tuple[str, str] | None:
    if pair is None:
        return None
    if len(pair) != 2:
        raise ValueError(f"expected a two-element date range [after, before], got {pair}")
    return pair[0], pair[1]


def attribute_values(
    database: str,
    the_type: str,
    groupname: str | list[str] | None = None,
    dates_between: list[str] | None = None,
    row_limit: int = 50,
    offset: int = 0,
) -> dict:
    """Vocabulary of one attribute type: distinct values with entity counts
    and first/last dates. Use it to check the possible values of a type
    (e.g. ``naturalidade``, ``jesuita-entrada``) before searching.

    Args:
        database: database name as shown by ``list_databases``.
        the_type: attribute type, e.g. ``"naturalidade"``.
        groupname: restrict to one Kleio group or a list of groups.
        dates_between: ``[from, to]`` Timelink date strings (exclusive).
        row_limit: page size.
        offset: page offset for paging.
    """
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 50, ctx.settings.max_rows)
    df = attribute_values_df(
        the_type=the_type,
        groupname=groupname,
        dates_between=_tuple_or_none(dates_between),
        db=db,
    )
    records = df_records(df)
    if not records:
        return empty_page()
    return page_slice(records, offset, limit)


def find_entities_by_attribute(
    database: str,
    the_type: str | list[str],
    the_value: str | list[str] | None = None,
    entity_type: str = "person",
    show_elements: list[str] | None = None,
    more_attributes: list[str] | None = None,
    dates_in: list[str] | None = None,
    name_like: str | None = None,
    row_limit: int = 30,
    offset: int = 0,
) -> dict:
    """The workhorse search: entities having a given attribute, with
    value/date/name filters, optionally enriched with further attributes.

    Args:
        database: database name as shown by ``list_databases``.
        the_type: attribute type or list of types; string allows ``%``
            wildcards (e.g. ``"jesuita-entrada%"``).
        the_value: value filter — string with ``%`` wildcards (e.g.
            ``"Coimbra%"``) or list for exact IN-match.
        entity_type: one of the values from ``db_schema`` (``person``,
            ``object``, ``act``, ``entity``, dynamic classes).
        show_elements: entity columns to include (default ``["name"]``).
        more_attributes: extra attribute types joined as columns.
        dates_in: ``[after, before]`` Timelink date strings, exclusive
            bounds on the attribute date.
        name_like: LIKE filter on the entity name.
        row_limit: page size.
        offset: page offset for paging.
    """
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 30, ctx.settings.max_rows)
    df = entities_with_attribute(
        the_type=the_type,
        the_value=the_value,
        entity_type=entity_type,
        show_elements=["name"] if show_elements is None else show_elements,
        more_attributes=more_attributes,
        dates_in=_tuple_or_none(dates_in),
        name_like=name_like,
        db=db,
    )
    records = df_records(df)
    if not records:
        return empty_page()
    return page_slice(records, offset, limit)


def find_persons_by_name(
    database: str,
    name: str,
    similar: bool = False,
    row_limit: int = 30,
    offset: int = 0,
) -> dict:
    """Persons whose name matches a pattern (or a fuzzy match with
    particles removed: ``similar=True`` strips ``de/da/dos/...`` and
    inserts ``%`` between components).

    Args:
        database: database name as shown by ``list_databases``.
        name: name to search; ``%`` wildcards allowed unless ``similar``.
        similar: fuzzy match with particles removed.
        row_limit: page size.
        offset: page offset for paging.
    """
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 30, ctx.settings.max_rows)
    try:
        df = pname_to_df(name, db=db, similar=similar)
    except IndexError:  # library quirk on empty result sets
        df = None
    records = df_records(df)
    if not records:
        return empty_page()
    return page_slice(records, offset, limit)


def entity_attributes(
    database: str,
    ids: list[str],
    entity_type: str = "person",
    include_attributes: list[str] | None = None,
    exclude_attributes: list[str] | None = None,
    show_elements: list[str] | None = None,
    row_limit: int = 100,
    offset: int = 0,
) -> dict:
    """All attributes of one or more entities — the "person profile"
    table, one row per attribute with type, value, date and obs.

    Args:
        database: database name as shown by ``list_databases``.
        ids: entity ids (e.g. from ``find_entities_by_attribute``).
        entity_type: one of the values from ``db_schema``.
        include_attributes: attribute types to include; wildcards allowed.
        exclude_attributes: attribute types to exclude.
        show_elements: entity columns to include (default ``["name"]``).
        row_limit: page size.
        offset: page offset for paging.
    """
    ctx = get_context()
    db = ctx.databases.get(database)
    limit = clamp_limit(row_limit, 100, ctx.settings.max_rows)
    df = group_attributes(
        group=ids,
        entity_type=entity_type,
        include_attributes=include_attributes,
        exclude_attributes=exclude_attributes,
        show_elements=["name"] if show_elements is None else show_elements,
        db=db,
    )
    records = df_records(df)
    if not records:
        return empty_page()
    return page_slice(records, offset, limit)


def entity_details(
    database: str,
    ids: list[str],
    format: str = "kleio",  # noqa: A002 (MCP parameter name)
) -> dict:
    """Full rendering of an entity in Kleio notation (or markdown where
    available) — the richest view of one entity, including inline
    relations, attributes and observations. At most 5 ids per call.

    Args:
        database: database name as shown by ``list_databases``.
        ids: entity ids, at most 5.
        format: ``kleio`` (default) or ``markdown`` (falls back to kleio
            for classes without a markdown renderer).
    """
    if not 1 <= len(ids) <= 5:
        raise ValueError(f"entity_details takes between 1 and 5 ids, got {len(ids)}")
    db = get_context().databases.get(database)
    details = []
    for eid in ids:
        with db.session() as session:
            entity = Entity.get_entity(eid, session)
            if entity is None:
                details.append({"id": eid, "error": "entity not found"})
                continue
            if format == "markdown" and hasattr(entity, "to_markdown"):
                text = entity.to_markdown()
            else:
                # render inside the session: to_kleio lazy-loads relations
                # and contained entities
                text = entity.to_kleio()
            details.append(
                {
                    "id": eid,
                    "entity_class": getattr(entity, "pom_class", None),
                    "text": text,
                }
            )
    return {"database": database, "format": format, "details": details}


def register(mcp) -> None:
    """Attach this module's tools to the FastMCP server."""
    mcp.tool(
        name="attribute_values",
        description=(
            "Vocabulary of one attribute type: distinct values with the number of "
            "distinct entities and first/last dates. Check the possible values "
            "of a type (naturalidade, grau, jesuita-entrada...) before "
            "searching with find_entities_by_attribute. "
            "Dates are Timelink strings (yyyy, yyyymm or yyyymmdd)."
        ),
    )(_wrapped(attribute_values))
    mcp.tool(
        name="find_entities_by_attribute",
        description=(
            "Main search tool: entities having a given attribute, with value/date/"
            "name filters, optionally enriched with further attributes "
            "(more_attributes). String filters use SQL LIKE wildcards (% and _); "
            "lists mean exact IN-match. Run attribute_values first to check the "
            "vocabulary. Returns paged rows keyed by entity id."
        ),
    )(_wrapped(find_entities_by_attribute))
    mcp.tool(
        name="find_persons_by_name",
        description=(
            "Persons whose name matches a pattern (% wildcards allowed), or a "
            "fuzzy match with similar=true (strips de/da/dos/... particles and "
            "inserts % between name components). Returns id, name, sex, obs."
        ),
    )(_wrapped(find_persons_by_name))
    mcp.tool(
        name="entity_attributes",
        description=(
            "All attributes of one or more entities — the person-profile table: "
            "one row per attribute with the_type, the_value, the_date, obs. "
            "Optional include/exclude attribute filters (wildcards allowed)."
        ),
    )(_wrapped(entity_attributes))
    mcp.tool(
        name="entity_details",
        description=(
            "Full rendering of up to 5 entities in Kleio notation (format=kleio) "
            "or markdown where available — the richest view of one entity, "
            "including inline relations, attributes and observations. Chain it "
            "after a search to inspect the interesting ids."
        ),
    )(_wrapped(entity_details))
