"""Timelink MCP server.

Exposes Timelink databases, searches, relations and the Kleio source-update
pipeline to AI agents through the Model Context Protocol.

The tool set is specified in ``docs/mcp-tools-draft.md`` (validated
2026-10-03). Run with ``timelink-mcp`` or ``python -m timelink.mcp``.
"""

from timelink.mcp.config import McpSettings
from timelink.mcp.context import ServerContext, configure, get_context, reset_context
from timelink.mcp.server import create_server

__all__ = [
    "McpSettings",
    "ServerContext",
    "configure",
    "create_server",
    "get_context",
    "reset_context",
]
