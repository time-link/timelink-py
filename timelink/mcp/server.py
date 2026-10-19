"""FastMCP server assembly: 18 tools in four groups plus the schema resource."""

from __future__ import annotations

from importlib import resources

try:  # mcp 2.x renamed FastMCP to MCPServer; the used API is identical
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

from timelink.mcp.context import get_context
from timelink.mcp.tools import ALL_MODULES

INSTRUCTIONS = """\
Timelink: person-related information from historical sources.

Workflows:
1. Discover: list_projects (what exists, including database-less
   projects) -> list_databases -> db_info -> db_schema.
2. Search: attribute_values (check the vocabulary) ->
   find_entities_by_attribute (LIKE wildcards % and _; lists are exact
   IN-match) -> entity_attributes / entity_details on interesting ids;
   find_persons_by_name for name searches; find_relations /
   entity_relations for the relation space.
3. Update: get_import_status -> translate_sources -> wait_for_translations
   (re-invoke while still_pending) -> import_from_sources ->
   get_import_status; get_translation_report / get_import_report for
   files with errors or warnings.

Dates are Timelink strings (yyyy, yyyymm or yyyymmdd) compared lexically.
Tabular tools page with row_limit/offset and return next_offset when more
rows exist. The database structure reference is the
timelink://schema/{database} resource.
"""


def load_db_structure() -> str:
    """The packaged database-structure reference (docs/mcp-db-structure-draft.md)."""
    return (resources.files("timelink.mcp") / "data" / "db-structure.md").read_text()


def create_server() -> FastMCP:
    """Build the FastMCP application with all tools and resources registered."""
    get_context()  # validate configuration early (bad env vars fail fast)
    mcp = FastMCP("timelink", instructions=INSTRUCTIONS)
    for module in ALL_MODULES:
        module.register(mcp)

    @mcp.resource(
        "timelink://schema/{database}",
        name="timelink-database-structure",
        description=(
            "Conceptual model of a Timelink database: entities, attributes, "
            "relations, provenance; table/view catalogue; date, id and "
            "wildcard conventions; query recipes."
        ),
    )
    def db_structure(database: str) -> str:  # pylint: disable=unused-argument
        return load_db_structure()

    return mcp


# Module-level instance: the entry point for `timelink-mcp` and
# `python -m timelink.mcp`.
mcp = create_server()
