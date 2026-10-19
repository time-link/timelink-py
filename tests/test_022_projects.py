"""Tests for structural project discovery (timelink.api.projects).

Docker-free: plain directories and marker files. The concept and the
layouts tested here are those of the timelink_home reference doc
(single project, multi-project, git-submodule subprojects, legacy MHK).
"""

from pathlib import Path

from timelink.api.projects import (
    get_timelink_projects,
    home_is_project,
    is_project,
    known_projects,
    project_for,
)


def _make(home: Path, *subdirs: str) -> None:
    for sub in subdirs:
        (home / sub).mkdir(parents=True, exist_ok=True)


def test_project_marker_file(tmp_path):
    """A bare directory with a .timelink-project marker is a project,
    even with none of the layout subdirectories."""
    marked = tmp_path / "marked"
    marked.mkdir()
    (marked / ".timelink-project").touch()
    assert is_project(marked) is True

    plain = tmp_path / "plain"
    plain.mkdir()
    assert is_project(plain) is False


def test_home_marker_is_not_a_project(tmp_path):
    """A .timelink-home marker identifies a multi-project home
    container, never a project itself; projects under it are found."""
    home = tmp_path / "home"
    _make(home, "sources", "projects/alpha/database/sqlite")
    (home / ".timelink-home").touch()

    assert is_project(home) is False
    projects = {p["name"]: p for p in get_timelink_projects(home)}
    assert "alpha" in projects
    # the multi-project home root is not a single-project home either
    assert home_is_project(home) is False


def test_all_documented_layouts(tmp_path):
    home = tmp_path / "home"
    _make(
        home,
        # legacy MHK project, sources never imported (no db file)
        "sources/legacy/database",
        "sources/legacy/structures",
        "sources/legacy/sources",
        # loose collection of sources with no database dir
        "sources/bare/sources",
        "sources/bare/identifications",
        # git-submodule subproject inside the parent's sources/
        "sources/legacy/sources/submod/database",
        "sources/legacy/sources/submod/structures",
        # multi-project layout plus system infrastructure
        "projects/alpha/database/sqlite",
        "system/database/sqlite",
        # a directory that is none of the above
        "sources/not-a-project/misc",
    )

    projects = {p["name"]: p for p in get_timelink_projects(home)}
    assert {"legacy", "bare", "submod", "alpha"} <= set(projects)
    assert "system" not in projects
    assert "not-a-project" not in projects
    assert "sources" not in projects  # the container itself

    # the gap the user cares about: project exists, no database yet
    assert projects["legacy"]["has_database"] is True  # has the directory
    assert projects["bare"]["has_database"] is False

    # submodule nesting is reported
    assert projects["submod"]["inside"] == "sources/legacy"
    assert projects["legacy"]["inside"] is None


def test_project_for_annotations(tmp_path):
    """Databases are attributed to their nearest project; the system
    users database belongs to none; a single-project home root is the
    project of its own databases."""
    home = tmp_path / "home"
    _make(
        home,
        "projects/alpha/database/sqlite",
        "sources/legacy/sources/submod/database/sqlite",
        "system/database/sqlite",
    )
    (home / "projects" / "alpha" / "database" / "sqlite" / "shared.sqlite").touch()
    submod_db = home / "sources" / "legacy" / "sources" / "submod" / "database" / "sqlite" / "sub.sqlite"
    submod_db.touch()
    (home / "system" / "database" / "sqlite" / "users.sqlite").touch()

    known = known_projects(home)
    assert project_for(home / "projects" / "alpha" / "database" / "sqlite" / "shared.sqlite", home, known) == "alpha"
    # nested: nearest project is the subproject, not the parent
    assert project_for(submod_db, home, known) == "submod"
    assert project_for(home / "system" / "database" / "sqlite" / "users.sqlite", home, known) is None

    # single-project home: the root itself is the project
    solo = tmp_path / "solo"
    _make(solo, "database/sqlite", "sources", "structures")
    solo_db = solo / "database" / "sqlite" / "one.sqlite"
    solo_db.touch()
    assert home_is_project(solo) is True
    assert get_timelink_projects(solo) == []  # nothing below the root
    assert project_for(solo_db, solo) == solo.name


def test_missing_root(tmp_path):
    """A missing search root yields an empty listing, not an error."""
    root = Path(tmp_path) / "no-such-home"
    assert get_timelink_projects(root) == []
    assert home_is_project(root) is False
    assert project_for(root / "database" / "sqlite" / "x.sqlite", root) is None
