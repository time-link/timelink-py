"""Discovery tools: list_projects, list_databases, db_info, db_schema (§3.1–3.4)."""

from __future__ import annotations

from timelink.mcp.context import get_context
from timelink.mcp.errors import tool_errors as _wrapped


def list_projects(directory: str | None = None) -> dict:
    """List the Timelink projects under the configured home.

    Projects are detected structurally — a ``.timelink-project``
    marker, ``database/``, ``structures/`` or ``sources/`` child
    directory — not from database files, so projects whose sources
    were never imported appear too (``has_database`` and ``databases``
    show the gap). Each entry carries its layout, the databases found
    inside it and, for git-submodule subprojects, the enclosing
    project (``inside``).

    Args:
        directory: search this root instead of the configured one.

    Returns:
        ``{root, projects: [{name, path, relative_path, marker,
        has_database, has_structures, has_sources, inside,
        databases: [{name, path}]}], project_count,
        databases_without_project}``.
    """
    return get_context().databases.list_projects(directory=directory)


def list_databases(db_type: str | None = None, directory: str | None = None) -> dict:
    """List the Timelink databases available on this machine.

    The configured root (the timelink home, by default) is searched
    recursively, so databases of every project under a multi-project home
    are listed, each annotated with its ``project``.

    Args:
        db_type: ``sqlite``, ``postgres`` or ``all``; None uses the
            server's configured default engine.
        directory: sqlite only — search this root instead of the
            configured one (listing only; connecting uses the
            configured root or an absolute path).

    Returns:
        ``{default_db_type, sqlite_root?, databases: [{name, project?,
        db_type, path?}]}``.
    """
    return get_context().databases.list_databases(db_type=db_type, directory=directory)


def db_info(database: str) -> dict:
    """Report what is in one database: row counts, entity classes, views, version.

    The "what is in this database" entry point — call it after
    ``list_databases`` and before ``db_schema``.

    Args:
        database: database name as shown by ``list_databases``; when the
            same name exists in several projects, use the qualified
            ``project/name`` form or a path.
    """
    db = get_context().databases.get(database)
    tables = [{"name": name, "rows": count} for name, count in db.table_row_count()]
    try:
        version = db.get_database_version()
    except Exception:  # alembic_version table may be absent on partial dbs
        version = None
    return {
        "database": database,
        "db_type": db.db_type,
        "tables": tables,
        "entity_classes": db.get_models_ids(),
        "views": db.view_names(),
        "version": version,
        "kleio_server_attached": db.get_kleio_server() is not None,
    }


def db_schema(database: str, model_or_table: str | None = None) -> dict:
    """Describe one entity class / table / view, or list the group→model mapping.

    Without ``model_or_table``, returns the Kleio-group → ORM-class
    mapping, which tells you which ``entity_type`` values and which
    attribute-bearing groups exist. The conceptual model and query recipes
    are in the ``timelink://schema/{database}`` resource.

    Args:
        database: database name as shown by ``list_databases``.
        model_or_table: entity class id (``person``), table name
            (``persons``) or view name (``nrelations``).
    """
    db = get_context().databases.get(database)
    if model_or_table is None:
        mapping = [{"group": group, "table": table, "model": model} for group, table, model in db.describe(None)]
        return {"database": database, "group_model_mapping": mapping}

    try:
        columns = db.get_columns(model_or_table)
    except ValueError:
        available = sorted(set(db.get_models_ids()) | set(db.view_names()) | set(db.db_table_names()))
        raise ValueError(
            f"'{model_or_table}' is not a known entity class, table or view "
            f"of database '{database}'. Available: {available}"
        ) from None

    described = [
        {
            "name": col.name,
            "type": str(col.type),
            "nullable": getattr(col, "nullable", None),
            "primary_key": bool(getattr(col, "primary_key", False)),
            "foreign_keys": [fk.target_fullname for fk in getattr(col, "foreign_keys", [])],
        }
        for col in columns
    ]
    return {"database": database, "target": model_or_table, "columns": described}


def register(mcp) -> None:
    """Attach this module's tools to the FastMCP server."""
    mcp.tool(
        name="list_projects",
        description=(
            "List the Timelink projects under the configured timelink home. "
            "Projects are detected structurally (a .timelink-project marker or a "
            "database/, structures/ or sources/ child directory), not from "
            "database files, so projects without a database yet are listed too "
            "— start here when orienting in a home; use list_databases for the "
            "databases themselves. Each entry carries layout flags, the "
            "databases found inside the project and, for git-submodule "
            "subprojects, the enclosing project (inside). Params: directory "
            "(overrides the search root for this listing)."
        ),
    )(_wrapped(list_projects))
    mcp.tool(
        name="list_databases",
        description=(
            "List the Timelink databases available on this machine. The configured "
            "timelink home is searched recursively, so every project of a "
            "multi-project home appears, each with its project annotation. Start "
            "here; pass a `database` name (or 'project/name' when ambiguous) from "
            "the result to every other tool. Params: db_type "
            "(sqlite|postgres|all, default from server config), directory (sqlite "
            "only, overrides the search root for this listing)."
        ),
    )(_wrapped(list_databases))
    mcp.tool(
        name="db_info",
        description=(
            "Report the contents of one database: row counts per table, entity "
            "classes, views, alembic version, whether a Kleio server is attached. "
            "The 'what is in this database' entry point. The database parameter "
            "accepts the name, 'project/name' when the name exists in several "
            "projects, or a path."
        ),
    )(_wrapped(db_info))
    mcp.tool(
        name="db_schema",
        description=(
            "Describe one entity class, table or view (columns and types), or — "
            "when called without model_or_table — list the Kleio-group to "
            "ORM-class mapping, which shows valid entity_type values and "
            "attribute-bearing groups. See also the timelink://schema/{database} "
            "resource for the conceptual model and query recipes."
        ),
    )(_wrapped(db_schema))
