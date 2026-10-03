"""Tool modules of the Timelink MCP server, one per group (§3)."""

from timelink.mcp.tools import attributes, discovery, relations, sources

ALL_MODULES = (discovery, attributes, relations, sources)

__all__ = ["ALL_MODULES", "attributes", "discovery", "relations", "sources"]
