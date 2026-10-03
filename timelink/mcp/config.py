"""Environment configuration for the Timelink MCP server.

All settings come from ``TIMELINK_MCP_*`` environment variables so the
server process can be configured once per deployment (see
``docs/mcp-tools-draft.md`` §1). Five variables; one — ``TIMELINK_MCP_HOME``
— covers a standard deployment:

============================  ==============================================  =========================
Variable                     Purpose                                        Default
============================  ==============================================  =========================
``TIMELINK_MCP_HOME``        timelink/kleio home: the root searched         ``~/.timelink``
                             recursively for ``*.sqlite`` databases and
                             the home of a locally started Kleio server
``TIMELINK_MCP_SQLITE_ROOT`` override the database search root when            ``TIMELINK_MCP_HOME``
                             databases live outside the home, or to narrow
                             scope to one directory
``TIMELINK_MCP_DB_TYPE``     ``sqlite`` or ``postgres``                     ``sqlite``
``TIMELINK_MCP_KLEIO_URL``   attach to a running Kleio server (with token)  none
``TIMELINK_MCP_KLEIO_TOKEN`` token for the running Kleio server               none
``TIMELINK_MCP_MAX_ROWS``    hard cap on rows returned per page             ``500``
============================  ==============================================  =========================

The home handles every documented layout of a timelink home (single
project ``<home>/database/sqlite``; multi-project
``<home>/projects/<project>/database/sqlite`` plus ``system``; project
with git-submodule subprojects ``<home>/sources/<sub>/database``; legacy
MHK ``<home>/sources/<project>/database``): the search root is walked
recursively, so all are discovered from the one root.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DB_TYPE_ENV = "TIMELINK_MCP_DB_TYPE"
HOME_ENV = "TIMELINK_MCP_HOME"
SQLITE_ROOT_ENV = "TIMELINK_MCP_SQLITE_ROOT"
KLEIO_URL_ENV = "TIMELINK_MCP_KLEIO_URL"
KLEIO_TOKEN_ENV = "TIMELINK_MCP_KLEIO_TOKEN"
MAX_ROWS_ENV = "TIMELINK_MCP_MAX_ROWS"

DEFAULT_MAX_ROWS = 500
DEFAULT_HOME = "~/.timelink"
VALID_DB_TYPES = ("sqlite", "postgres")


@dataclass(frozen=True)
class McpSettings:
    """Deployment settings for one MCP server process.

    Attributes:
        db_type: default database engine (``sqlite`` or ``postgres``).
        home: the timelink/kleio home. Used as the recursive search root
            for sqlite databases and as the home of a Kleio server started
            locally. None resolves to ``~/.timelink``.
        sqlite_root: override for the database search root, for the cases
            where databases are not under the home: a query-only
            deployment with no Kleio sources, or databases kept elsewhere
            or scope narrowed to one directory. None resolves to the home.
        kleio_url: url of an already running Kleio server to attach to
            (preferred over starting one when set, together with
            ``kleio_token``).
        kleio_token: admin token for ``kleio_url``.
        max_rows: hard cap on rows returned per page by any tool.
    """

    db_type: str = "sqlite"
    home: str | None = None
    sqlite_root: str | None = None
    kleio_url: str | None = None
    kleio_token: str | None = None
    max_rows: int = DEFAULT_MAX_ROWS

    def __post_init__(self):
        if self.db_type not in VALID_DB_TYPES:
            raise ValueError(f"db_type must be one of {VALID_DB_TYPES}, got {self.db_type!r}")
        if self.max_rows < 1:
            raise ValueError(f"max_rows must be >= 1, got {self.max_rows}")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "McpSettings":
        """Build settings from environment variables (or a supplied mapping)."""
        env = os.environ if env is None else env
        db_type = env.get(DB_TYPE_ENV, "sqlite")
        max_rows = int(env.get(MAX_ROWS_ENV, str(DEFAULT_MAX_ROWS)))
        return cls(
            db_type=db_type,
            home=env.get(HOME_ENV),
            sqlite_root=env.get(SQLITE_ROOT_ENV),
            kleio_url=env.get(KLEIO_URL_ENV),
            kleio_token=env.get(KLEIO_TOKEN_ENV),
            max_rows=max_rows,
        )

    def resolved_home(self) -> Path:
        """The home actually used: configured value or ``~/.timelink``."""
        return Path(self.home or DEFAULT_HOME).expanduser()

    def resolved_sqlite_root(self) -> Path:
        """The root searched recursively for sqlite databases."""
        if self.sqlite_root:
            return Path(self.sqlite_root).expanduser()
        return self.resolved_home()
