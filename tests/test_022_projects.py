"""Tests for structural project discovery and creation (timelink.api.projects).

Docker-free: plain directories and marker files. The concept and the
layouts tested here are those of the timelink_home reference doc
(single project, multi-project, git-submodule subprojects, legacy MHK).
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from timelink.api.projects import (
    CREATED_SUBDIRS,
    create_project,
    get_timelink_projects,
    home_is_project,
    is_project,
    known_projects,
    project_for,
)
from timelink.cli import app
from timelink.kleio.kleio_server import KleioServer


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


# =====================
# Project creation
# =====================


def test_create_project_scaffolds_discoverable_project(tmp_path):
    """The scaffold matches the layout that discovery detects: markers,
    project subdirectories, and the home container are all in place."""
    home = tmp_path / "home"
    project = create_project("demo", home)
    assert project["name"] == "demo"
    assert project["path"] == str(home / "projects" / "demo")

    project_dir = home / "projects" / "demo"
    assert (project_dir / ".timelink-project").is_file()
    for sub, _, _ in CREATED_SUBDIRS:
        assert (project_dir / sub).is_dir()
        assert (project_dir / sub / "README.md").is_file()

    # a fresh home is a full multi-project home
    assert (home / ".timelink-home").is_file()
    assert (home / "system" / "db" / "sqlite").is_dir()

    # ... and the project is discovered with the strict layout facts
    projects = {p["name"]: p for p in get_timelink_projects(home)}
    assert projects["demo"]["marker"] is True
    assert projects["demo"]["has_database"] is True
    assert projects["demo"]["has_structures"] is True
    assert projects["demo"]["has_sources"] is True
    assert home_is_project(home) is False  # the home is a container, not a project


def test_create_project_is_a_kleio_home(tmp_path):
    """The Kleio server home finder recognizes the scaffolded home."""
    home = tmp_path / "home"
    create_project("demo", home)
    assert KleioServer.find_local_kleio_home(str(home)) == str(home)


def test_create_project_in_existing_home(tmp_path):
    """Projects are added to an existing home; neighbors are untouched."""
    home = tmp_path / "home"
    _make(home, "projects/alpha/database/sqlite")
    create_project("demo", home)
    names = {p["name"] for p in get_timelink_projects(home)}
    assert {"alpha", "demo"} <= names


def test_create_project_refuses_existing_directory(tmp_path):
    """An existing project directory is refused unless force fills in
    its missing parts."""
    home = tmp_path / "home"
    create_project("demo", home)
    with pytest.raises(FileExistsError):
        create_project("demo", home)

    shutil.rmtree(home / "projects" / "demo" / "structures")
    project = create_project("demo", home, force=True)
    assert (home / "projects" / "demo" / "structures").is_dir()
    assert project["has_structures"] is True


def test_create_project_invalid_names(tmp_path):
    """Only plain directory names are accepted."""
    for bad in ("", ".", "..", ".hidden", "a/b", "a\\b"):
        with pytest.raises(ValueError):
            create_project(bad, tmp_path / "home")


def test_create_project_refuses_project_home(tmp_path):
    """A single-project directory cannot double as a multi-project home."""
    root = tmp_path / "root"
    _make(root, "sources", "structures")
    with pytest.raises(ValueError):
        create_project("demo", root)


def test_create_project_defaults_to_cwd(tmp_path, monkeypatch):
    """Without a home the project is created below the current directory."""
    monkeypatch.chdir(tmp_path)
    create_project("demo")
    assert (tmp_path / "projects" / "demo" / ".timelink-project").is_file()
    assert (tmp_path / ".timelink-home").is_file()


def test_cli_create_local(tmp_path):
    """`timelink create local` scaffolds the project and reports failures."""
    runner = CliRunner()
    home = tmp_path / "home"

    result = runner.invoke(app, ["create", "local", "demo", "--home", str(home)])
    assert result.exit_code == 0
    assert "created" in result.output
    assert (home / "projects" / "demo" / ".timelink-project").is_file()

    again = runner.invoke(app, ["create", "local", "demo", "--home", str(home)])
    assert again.exit_code == 1
    assert "already exists" in again.output
