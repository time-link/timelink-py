"""Kleio server lifecycle and per-database translation state.

One Kleio server per MCP server process, started lazily (only the
source-update tools touch it): either attached to a running server
(``TIMELINK_MCP_KLEIO_URL`` + ``TIMELINK_MCP_KLEIO_TOKEN``) or started in
Docker with the configured home (``TIMELINK_MCP_HOME``). The manager also
remembers the paths requested by the last ``translate_sources`` call per
database, so ``wait_for_translations`` knows what to wait for without the
agent passing paths around.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from timelink.api.database import TimelinkDatabase
from timelink.kleio import KleioServer
from timelink.mcp.config import McpSettings

logger = logging.getLogger(__name__)


@dataclass
class TranslateRequest:
    """The files ``translate_sources`` asked the Kleio server to translate."""

    source_path: str
    recurse: bool
    paths: list[str] = field(default_factory=list)


class KleioServerManager:
    """Lazily started/attached Kleio server plus translation bookkeeping."""

    def __init__(self, settings: McpSettings):
        self._settings = settings
        self._server: KleioServer | None = None
        self._translate_requests: dict[tuple[str, str], TranslateRequest] = {}

    @property
    def settings(self) -> McpSettings:
        return self._settings

    def use_server(self, server: KleioServer) -> None:
        """Inject an already-connected Kleio server (used by tests)."""
        self._server = server

    def get_server(self) -> KleioServer:
        """Return the Kleio server, attaching or starting one on first use.

        The started server uses the configured home (``TIMELINK_MCP_HOME``,
        default ``~/.timelink``); attaching to a running server takes
        precedence when url and token are configured.

        Raises:
            ValueError: when no server can be provisioned because neither
                ``TIMELINK_MCP_KLEIO_URL``/``TOKEN`` nor a usable home is
                configured.
        """
        if self._server is not None:
            return self._server
        s = self._settings
        home = s.resolved_home()
        if s.kleio_url and s.kleio_token:
            logger.info("Attaching to Kleio server at %s", s.kleio_url)
            self._server = KleioServer.attach(s.kleio_url, s.kleio_token, kleio_home=str(home))
        elif home.is_dir():
            logger.info("Starting Kleio server with kleio_home=%s", home)
            self._server = KleioServer.start(kleio_home=str(home))
        else:
            raise ValueError(
                "No Kleio server available. Set TIMELINK_MCP_HOME to the "
                "timelink home (starts a Docker container on first use of an "
                "update tool) or TIMELINK_MCP_KLEIO_URL and "
                "TIMELINK_MCP_KLEIO_TOKEN (attach to a running server)."
            )
        return self._server

    def ensure_attached(self, db: TimelinkDatabase) -> KleioServer:
        """Return the Kleio server, attaching it to ``db`` if needed."""
        server = db.get_kleio_server()
        if server is None:
            server = self.get_server()
            db.set_kleio_server(server)
        return server

    def remember_translate_request(
        self, db_key: tuple[str, str], source_path: str, recurse: bool, paths: list[str]
    ) -> None:
        self._translate_requests[db_key] = TranslateRequest(source_path=source_path, recurse=recurse, paths=list(paths))

    def last_translate_request(self, db_key: tuple[str, str]) -> TranslateRequest | None:
        return self._translate_requests.get(db_key)
