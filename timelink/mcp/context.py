"""Server-wide context: settings plus the database and Kleio managers.

A single context per server process, built lazily from the environment.
Tests replace it with :func:`configure` to point the managers at
temporary directories and an already-running Kleio server.
"""

from __future__ import annotations

from dataclasses import dataclass

from timelink.mcp.config import McpSettings
from timelink.mcp.databases import DatabaseManager
from timelink.mcp.kleio import KleioServerManager


@dataclass
class ServerContext:
    """The state shared by all tools of one MCP server process."""

    settings: McpSettings
    databases: DatabaseManager
    kleio: KleioServerManager


_context: ServerContext | None = None


def configure(settings: McpSettings) -> ServerContext:
    """Install a context built from ``settings``, replacing any previous one."""
    global _context
    _context = ServerContext(
        settings=settings,
        databases=DatabaseManager(settings),
        kleio=KleioServerManager(settings),
    )
    return _context


def get_context() -> ServerContext:
    """Return the current context, building one from the environment if needed."""
    if _context is None:
        configure(McpSettings.from_env())
    return _context


def reset_context() -> None:
    """Drop the current context (next ``get_context`` rebuilds from env)."""
    global _context
    _context = None
