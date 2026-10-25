"""Discovery and creation of Timelink projects in a home directory.

A project is the association of a set of Kleio sources with a database
(see the ``timelink_home`` reference in timelink-docs). Normally that
association lives in a directory of the filesystem, which is what this
module discovers: a directory below the search root that carries a
``.timelink-project`` marker, or has a ``database/``, ``structures/``
or ``sources/`` child, is a project. Discovery based on database files
alone (``get_sqlite_databases``) misses projects whose sources were
never imported — those appear here too, with ``has_database`` showing
the gap. A ``.timelink-home`` marker instead identifies a multi-project
home container, which is never a project itself.

Every documented home layout is covered by walking the one root:
single project (the root has the project layout), multi-project
(``projects/<project>/database/sqlite`` plus ``system``), project with
git-submodule subprojects (nested in a parent project's ``sources/``,
reported with ``inside`` set) and legacy MHK (``sources/<project>``).

The web application keeps its own project registry (``Project`` model
in the users database, which can also represent distributed projects
through ``databaseURL`` / ``kleioServerURL``); ``TimelinkWebApp``
feeds it from this filesystem discovery. Projects without a directory
(only reachable through the registry) are invisible here by design.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_MARKER = ".timelink-project"
HOME_MARKER = ".timelink-home"
STRICT_SUBDIRS = ("database", "structures")  # unambiguous project layout
LOOSE_SUBDIRS = ("sources",)  # Kleio sources not imported yet; not proof at the root

# Subdirectories scaffolded by create_project, each with a README
# placeholder so the layout survives in git (empty directories do not):
# (subdirectory, README title, README text).
CREATED_SUBDIRS = (
    ("database/sqlite", "SQLite databases", "SQLite database files of this project."),
    ("inferences", "Inferences", "Information deduced from the sources (for instance, same-as identifications)."),
    ("notebooks", "Notebooks", "Analysis notebooks for this project."),
    (
        "sources",
        "Kleio sources",
        "Kleio source files (`.cli`, `.kleio`), their XML translations and translation reports (`.rpt`).",
    ),
    ("structures", "Structures", "Kleio structure files describing the internal structure of the historical sources."),
)

# Never walked into (nothing nests there that can be a project).
PRUNE_NAMES = {"database", "structures", "notebooks", "__pycache__", "node_modules"}
# Multi-project home infrastructure, not a project (direct child of the root).
HOME_INFRASTRUCTURE = {"system"}


def project_layout(path: Path) -> dict:
    """Structural facts of one candidate directory (no walking).

    Returns ``{marker, home_marker, has_database, has_structures,
    has_sources}``; all False for a missing or unreadable directory.
    """
    try:
        children = {entry.name for entry in os.scandir(path) if entry.is_dir()}
    except OSError:
        return {
            "marker": False,
            "home_marker": False,
            "has_database": False,
            "has_structures": False,
            "has_sources": False,
        }
    return {
        "marker": (path / PROJECT_MARKER).is_file(),
        "home_marker": (path / HOME_MARKER).is_file(),
        "has_database": "database" in children,
        "has_structures": "structures" in children,
        "has_sources": "sources" in children,
    }


def is_project_layout(layout: dict) -> bool:
    """A project directory: marker or project subdirectories, and not a
    home container (``.timelink-home`` marks multi-project homes)."""
    if layout["home_marker"]:
        return False
    return layout["marker"] or layout["has_database"] or layout["has_structures"] or layout["has_sources"]


def is_strict_project_layout(layout: dict) -> bool:
    """The stricter rule applied to the search root itself: a bare
    ``sources/`` child at the root is the legacy-MHK container of
    projects, not a project of its own."""
    if layout["home_marker"]:
        return False
    return layout["marker"] or layout["has_database"] or layout["has_structures"]


def is_project(path: Path) -> bool:
    """Structural test: is this directory a Timelink project?"""
    return is_project_layout(project_layout(path))


def home_is_project(root: Path) -> bool:
    """Whether the root is itself a single-project home layout."""
    return is_strict_project_layout(project_layout(root))


def discover_projects(root: Path) -> list[dict]:
    """Walk the root and describe every project directory below it.

    Returns one entry per project, sorted by ``relative_path``:
    ``{name, path, relative_path, marker, has_database, has_structures,
    has_sources, inside}`` where ``inside`` is the relative path of the
    nearest enclosing project (None for top-level projects).
    """
    projects: list[dict] = []
    if not root.is_dir():
        return projects

    stack: list[tuple[Path, str | None]] = [(root, None)]  # (directory, enclosing project)
    while stack:
        directory, inside = stack.pop()
        is_root = directory == root
        layout = project_layout(directory)
        relative = directory.relative_to(root).as_posix()
        enclosing = inside
        if not is_root and is_project_layout(layout):
            projects.append(
                {
                    "name": directory.name,
                    "path": str(directory),
                    "relative_path": relative,
                    **layout,
                    "inside": inside,
                }
            )
            enclosing = relative
        try:
            children = [entry for entry in os.scandir(directory) if entry.is_dir() and not entry.is_symlink()]
        except OSError:
            continue
        for entry in children:
            if entry.name.startswith(".") or entry.name in PRUNE_NAMES:
                continue
            if is_root and entry.name in HOME_INFRASTRUCTURE:
                continue
            stack.append((Path(entry.path), enclosing))
    return sorted(projects, key=lambda project: project["relative_path"])


def get_timelink_projects(directory_path: str | Path | None = None) -> list[dict]:
    """List the Timelink projects in a home directory.

    The counterpart of :func:`timelink.api.database_sqlite.get_sqlite_databases`
    for projects: structural discovery, so projects without a database
    yet are listed. See :func:`discover_projects` for the entry shape.

    Args:
        directory_path: the timelink home to search; None searches the
            current working directory (as the CLI does).
    """
    root = Path(directory_path or os.getcwd())
    return discover_projects(root)


def create_project(name: str, home: str | Path | None = None, *, force: bool = False) -> dict:
    """Scaffold a new Timelink project in a home directory.

    Creates ``<home>/projects/<name>`` with the project layout
    (``sources``, ``structures``, ``database/sqlite``, ``inferences``,
    ``notebooks``) and the ``.timelink-project`` marker; the home root
    gets the ``.timelink-home`` marker when it does not have it yet,
    and ``system/db/sqlite`` when the home is created from scratch.
    The result is discoverable by :func:`discover_projects` and
    recognized by ``KleioServer.find_local_kleio_home``.

    Args:
        name: name of the project; used as the directory name, so it
            must be a plain directory name (no path separators, not
            starting with a dot).
        home: the timelink home root; None uses the current working
            directory, as the CLI does. The home is created when
            missing. Must not itself be a project directory.
        force: when the project directory already exists, fill in the
            missing parts instead of raising; the default refuses, so
            an unrelated directory is never taken over silently.

    Returns:
        The created project in the :func:`discover_projects` entry
        shape (``name``, ``path``, layout facts).

    Raises:
        ValueError: invalid project name, or the home is itself a
            project directory, or the target path exists and is not a
            directory.
        FileExistsError: the project directory already exists and
            ``force`` is False.
    """
    if not name or name in (".", "..") or name.startswith(".") or "/" in name or "\\" in name:
        raise ValueError(f"invalid project name: {name!r} (must be a plain directory name)")
    root = Path(home) if home is not None else Path.cwd()
    if home_is_project(root):
        raise ValueError(
            f"{root} is itself a project directory; use its parent or a dedicated home as the timelink home"
        )
    home_existed = root.is_dir()
    project_dir = root / "projects" / name
    if project_dir.exists() and not project_dir.is_dir():
        raise ValueError(f"{project_dir} exists and is not a directory")
    if project_dir.is_dir() and not force:
        raise FileExistsError(f"project directory already exists: {project_dir} (use force to fill in missing parts)")
    for sub, title, readme in CREATED_SUBDIRS:
        (project_dir / sub).mkdir(parents=True, exist_ok=True)
        readme_path = project_dir / sub / "README.md"
        if not readme_path.exists():
            readme_path.write_text(f"# {title}\n\n{readme}\n", encoding="utf-8")
    marker = project_dir / PROJECT_MARKER
    if not marker.exists():
        marker.touch()
    if not (root / HOME_MARKER).exists():
        (root / HOME_MARKER).touch()
    if not home_existed:
        (root / "system" / "db" / "sqlite").mkdir(parents=True, exist_ok=True)
    return {"name": name, "path": str(project_dir), **project_layout(project_dir)}


def project_dirs(root: Path) -> set[Path]:
    """Paths of the project directories below the root (root excluded)."""
    return {Path(project["path"]) for project in discover_projects(root)}


def known_projects(root: Path) -> set[Path]:
    """Project directories of the root, plus the root itself when the
    home is a single-project layout (strict rule)."""
    known = project_dirs(root)
    if home_is_project(root):
        known.add(root)
    return known


def nearest_project(path: Path, root: Path, known: set[Path]) -> Path | None:
    """The nearest ancestor of ``path`` (itself included, root included)
    that is one of the ``known`` project directories; None when the
    path is outside every project."""
    try:
        parts = path.relative_to(root).parts
    except ValueError:
        return None
    for depth in range(len(parts), -1, -1):
        ancestor = root.joinpath(*parts[:depth])
        if ancestor in known:
            return ancestor
    return None


def project_for(path: Path, root: Path, known: set[Path] | None = None) -> str | None:
    """The project a path belongs to: the name of the nearest ancestor
    directory discovered as a project. In a single-project home (the
    root itself has the project layout) that is the root's name; paths
    under home infrastructure such as ``system`` or otherwise outside
    any project get None.
    """
    known = known_projects(root) if known is None else known
    nearest = nearest_project(path.parent, root, known)
    return nearest.name if nearest is not None else None
