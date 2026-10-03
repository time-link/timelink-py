"""Database connection manager for the Timelink MCP server.

The configured root (``TIMELINK_MCP_SQLITE_ROOT``, default
``TIMELINK_MCP_HOME``) is walked recursively, so databases are found in
every documented timelink-home layout: single project, multi-project
(``projects/<project>/database/sqlite``), project with git-submodule
subprojects and legacy MHK (``sources/<project>/database``). Each
database is annotated with the project it belongs to — the nearest
ancestor directory discovered as a project by the structural rules of
:mod:`timelink.api.projects`), which also cover projects without any
database yet. Projects themselves are listed by ``list_projects``,
independently of databases.

Connecting never creates a database: a name that does not resolve to an
existing file raises, so agents cannot accidentally materialize empty
databases from a typo. When the same database name exists in several
projects, connect with the qualified ``project/name`` form or a path.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from timelink.api.database import TimelinkDatabase
from timelink.api.database_postgres import get_postgres_dbnames
from timelink.api.projects import (
    PROJECT_MARKER,
    discover_projects,
    known_projects,
    nearest_project,
    project_for,
    project_layout,
)
from timelink.mcp.config import McpSettings

logger = logging.getLogger(__name__)

__all__ = ["DatabaseManager", "project_for", "PROJECT_MARKER"]


class DatabaseManager:
    """Cache of TimelinkDatabase instances, keyed by resolved database."""

    def __init__(self, settings: McpSettings):
        self._settings = settings
        self._databases: dict[tuple[str, str], TimelinkDatabase] = {}

    @property
    def settings(self) -> McpSettings:
        return self._settings

    def _sqlite_index(self, root: Path) -> dict[Path, dict]:
        """Index the ``*.sqlite`` files reachable under ``root``:
        ``{path: {name, project}}``.

        In every documented layout databases live inside a project's
        ``database/`` subtree, in the home's ``system`` infrastructure, or
        as stray files directly inside a project directory — so only
        those places are walked. A full recursive walk of a real home is
        dominated by Kleio artifacts and vendored trees (200k+ entries
        under ``sources/``), which made listings time out in MCP clients.

        Only ``*.sqlite`` files are indexed — the extension
        :class:`TimelinkDatabase` connects to; a stray ``*.db`` file would
        make it silently create a new ``*.sqlite`` alongside.
        """
        if not root.is_dir():
            return {}
        known = known_projects(root)
        index: dict[Path, dict] = {}

        def add(path: Path) -> None:
            if path.suffix == ".sqlite":
                index[path] = {"name": path.stem, "project": project_for(path, root, known)}

        def database_dirs(directory: Path) -> list[Path]:
            """Child directories of ``directory`` that hold databases.

            Matches ``database`` and path-bug variants like
            ``database\\sqlite`` (a directory whose name contains a
            backslash); never matches the big ``sources/`` trees.
            """
            try:
                entries = os.scandir(directory)
            except OSError:
                return []
            with entries:
                return [
                    Path(entry.path)
                    for entry in entries
                    if entry.is_dir() and not entry.is_symlink() and "database" in entry.name.lower()
                ]

        bases = [base for project in sorted(known) for base in database_dirs(project)]
        bases.append(root / "system")  # multiproject home infrastructure
        for base in bases:
            if base.is_dir():
                for dirpath, _dirnames, filenames in os.walk(base):
                    for filename in filenames:
                        add(Path(dirpath) / filename)

        # stray *.sqlite directly inside a project directory or the root
        # (e.g. path-bug artifacts like 'database\sqlite.sqlite')
        for directory in [*sorted(known), root]:
            try:
                entries = os.scandir(directory)
            except OSError:
                continue
            with entries:
                for entry in entries:
                    if entry.is_file():
                        add(Path(entry.path))
        return index

    def list_databases(self, db_type: str | None = None, directory: str | None = None) -> dict:
        """List the Timelink databases visible to this server.

        Args:
            db_type: restrict to ``sqlite``, ``postgres`` or ``all``; None
                uses the configured default engine.
            directory: sqlite only — search this root instead of the
                configured one (listing only; connecting uses the
                configured root or an absolute path).

        Returns:
            dict with the configured ``default_db_type``, the ``sqlite_root``
            in effect, a ``databases`` list of ``{name, project?, db_type,
            path}`` and, when a listing fails (e.g. Docker not running for
            postgres), an error field.
        """
        wanted = db_type or self._settings.db_type
        if wanted not in ("sqlite", "postgres", "all"):
            raise ValueError("db_type must be 'sqlite', 'postgres' or 'all'")

        result: dict = {
            "default_db_type": self._settings.db_type,
            "databases": [],
        }
        if wanted in ("sqlite", "all"):
            root = Path(directory).expanduser() if directory else self._settings.resolved_sqlite_root()
            result["sqlite_root"] = str(root)
            if root.is_dir():
                for path, info in sorted(self._sqlite_index(root).items()):
                    result["databases"].append(
                        {
                            "name": info["name"],
                            "project": info["project"],
                            "db_type": "sqlite",
                            "path": str(path),
                        }
                    )
            else:
                result["sqlite_error"] = f"search root does not exist: {root}"
        if wanted in ("postgres", "all"):
            try:
                for name in get_postgres_dbnames():
                    result["databases"].append({"name": name, "db_type": "postgres"})
            except Exception as exc:  # docker down, no postgres container
                logger.warning("Could not list postgres databases: %s", exc)
                result["postgres_error"] = str(exc)
        return result

    def list_projects(self, directory: str | None = None) -> dict:
        """List the Timelink projects under the search root.

        Projects are detected structurally (``.timelink-project``
        marker, ``database/``, ``structures/`` or ``sources/`` child),
        so projects without a database yet are listed too — use this,
        not ``list_databases``, to see what exists in the home. Each
        entry carries its layout flags, the databases found inside it
        and, for subprojects, the enclosing project.

        Args:
            directory: search this root instead of the configured one.

        Returns:
            dict with the ``root`` in effect, a ``projects`` list of
            ``{name, path, relative_path, marker, has_database,
            has_structures, has_sources, inside, databases}`` entries
            (``is_home`` marks the single-project-home root), the
            ``project_count`` and the number of databases outside any
            project (``databases_without_project``).
        """
        root = Path(directory).expanduser() if directory else self._settings.resolved_sqlite_root()
        result: dict = {"root": str(root), "projects": []}
        if not root.is_dir():
            result["error"] = f"search root does not exist: {root}"
            return result

        known = known_projects(root)
        by_project: dict[Path, list[dict]] = {}
        orphans = 0
        for path, info in sorted(self._sqlite_index(root).items()):
            owner = nearest_project(path.parent, root, known)
            if owner is None:
                orphans += 1
                continue
            by_project.setdefault(owner, []).append({"name": info["name"], "path": str(path)})

        entries = []
        for project in discover_projects(root):
            entry = dict(project)
            entry["databases"] = by_project.get(Path(project["path"]), [])
            entries.append(entry)
        if root in known:  # single-project home: the root is the project
            entries.append(
                {
                    "name": root.name,
                    "path": str(root),
                    "relative_path": ".",
                    "is_home": True,
                    **project_layout(root),
                    "inside": None,
                    "databases": by_project.get(root, []),
                }
            )
        entries.sort(key=lambda entry: entry["relative_path"])
        result["projects"] = entries
        result["project_count"] = len(entries)
        result["databases_without_project"] = orphans
        return result

    def _describe(self, path: Path, info: dict) -> str:
        return f"{info['project']}/{info['name']} ({path})" if info["project"] else f"{info['name']} ({path})"

    def _resolve_sqlite(self, database: str) -> Path:
        """Resolve a database reference to an existing ``*.sqlite`` file.

        Accepted forms, tried in order: an absolute file path; a path
        relative to the search root; the unique file-stem name; the
        qualified ``project/name``. Ambiguous or unknown references raise
        with the available candidates.
        """
        root = self._settings.resolved_sqlite_root()
        index = self._sqlite_index(root)

        candidate = Path(database).expanduser()
        if candidate.is_absolute():
            if candidate.suffix == ".sqlite" and candidate.is_file():
                return candidate
        else:
            for relative in (candidate, candidate.with_suffix(".sqlite")):
                under_root = root / relative
                if under_root.suffix == ".sqlite" and under_root.is_file():
                    return under_root

        matches = [
            p
            for p, info in index.items()
            if info["name"] == database or f"{info['project']}/{info['name']}" == database
        ]
        if len(matches) > 1:
            candidates = ", ".join(self._describe(p, index[p]) for p in sorted(matches))
            raise ValueError(
                f"database name '{database}' is ambiguous in {root}: {candidates}. "
                "Use the 'project/name' form or a path."
            )
        if len(matches) == 1:
            return matches[0]
        available = sorted(
            {
                info["name"] if info["project"] is None else f"{info['project']}/{info['name']}"
                for info in index.values()
            }
        )
        raise ValueError(f"sqlite database '{database}' not found under {root}. Available: {available}")

    def get(self, database: str, db_type: str | None = None) -> TimelinkDatabase:
        """Return the (cached) TimelinkDatabase for ``database``.

        Args:
            database: database name as reported by ``list_databases``;
                for sqlite also a ``project/name`` qualified name or a
                path when the bare name is ambiguous.
            db_type: ``sqlite`` or ``postgres``; None uses the configured
                default engine.

        Raises:
            ValueError: when the database does not already exist — the
                manager never creates databases.
        """
        wanted = db_type or self._settings.db_type
        if wanted not in ("sqlite", "postgres"):
            raise ValueError(f"db_type must be 'sqlite' or 'postgres', got {wanted!r}")

        if wanted == "sqlite":
            path = self._resolve_sqlite(database)
            key = ("sqlite", str(path))
            cached = self._databases.get(key)
            if cached is not None:
                return cached
            db = TimelinkDatabase(db_name=path.stem, db_type="sqlite", db_path=str(path.parent))
        else:
            key = ("postgres", database)
            cached = self._databases.get(key)
            if cached is not None:
                return cached
            try:
                available = get_postgres_dbnames()
            except Exception as exc:
                raise ValueError(f"could not list postgres databases: {exc}") from exc
            if database not in available:
                raise ValueError(f"postgres database '{database}' not found. Available: {available}")
            db = TimelinkDatabase(db_name=database, db_type="postgres")

        self._databases[key] = db
        return db

    def project_of(self, database: str, db_type: str | None = None) -> str | None:
        """The project a database belongs to (None when not in a project).

        Source-update tools use this to scope their default path to the
        database's own project in a multi-project home.
        """
        wanted = db_type or self._settings.db_type
        if wanted != "sqlite":
            return None
        try:
            return project_for(self._resolve_sqlite(database), self._settings.resolved_sqlite_root())
        except ValueError:
            return None

    def db_key(self, database: str, db_type: str | None = None) -> tuple[str, str]:
        """Stable key used to remember per-database Kleio state."""
        wanted = db_type or self._settings.db_type
        if wanted == "sqlite":
            return ("sqlite", str(self._resolve_sqlite(database)))
        return (wanted, database)
