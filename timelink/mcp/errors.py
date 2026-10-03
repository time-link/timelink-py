"""Tool error surfacing for the Timelink MCP server.

The tools raise :class:`ValueError` with guidance for the agent (unknown
database, ambiguous name with candidate list, bad parameter). Whether
that message reaches the client depends on the SDK generation: mcp 1.x
includes the text of any exception, mcp 2.x only preserves
:class:`ToolError` messages and hides everything else behind a generic
"Error executing tool" string. Wrapping at registration time keeps the
guidance visible on both.
"""

from __future__ import annotations

import functools

try:  # mcp 2.x
    from mcp.server.mcpserver.tools.base import ToolError
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp.exceptions import ToolError

__all__ = ["ToolError", "tool_errors"]


def tool_errors(fn):
    """Convert the tool's exceptions to ToolError so messages survive.

    :class:`ValueError` keeps its message verbatim — that is the form the
    tools use for actionable guidance. Any other exception is prefixed
    with its type name so agents still see what went wrong.
    """

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except ValueError as exc:
            raise ToolError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - surface, never hide
            raise ToolError(f"{type(exc).__name__}: {exc}") from exc

    return wrapper
