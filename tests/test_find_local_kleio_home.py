"""Tests for find_local_kleio_home marker detection.

A project directory can live inside a multi-project home and be used
either as a single project (kleio home is the project directory) or as
part of the multi-project home (kleio home is the home directory),
depending on where detection starts. Marker files (.timelink-project,
.timelink-home) drive the detection; the nearest marker upwards wins.
"""

import pytest
from pathlib import Path

from timelink.kleio.kleio_server import (
    find_local_kleio_home,
    is_project_directory,
    is_timelink_home_directory,
)


def make_project(parent: Path, name: str, marker: bool = True) -> Path:
    """Create a minimal kleio project directory, with or without marker."""
    project = parent / name
    (project / "sources").mkdir(parents=True)
    if marker:
        (project / ".timelink-project").write_text("# timelink project\n")
    return project


def make_multi_home(parent: Path, name: str = "multi-home") -> Path:
    """Create a minimal multi-project home directory with marker."""
    home = parent / name
    (home / "projects").mkdir(parents=True)
    (home / ".timelink-home").write_text("# timelink home\n")
    return home


def test_standalone_project_found_from_subdirectory(tmp_path, monkeypatch):
    # a project cloned from the template, with marker, no legacy home names around
    project = make_project(tmp_path, "my-project")
    deep = project / "sources" / "deep"
    deep.mkdir()

    monkeypatch.chdir(deep)
    assert find_local_kleio_home() == str(project.resolve())

    # the same detection when the starting point is given as an argument
    assert find_local_kleio_home(str(deep)) == str(project.resolve())


def test_nested_project_used_as_single_project(tmp_path, monkeypatch):
    # a marked project inside a marked multi-project home: starting inside
    # the project detects the project itself, not the enclosing home
    home = make_multi_home(tmp_path)
    project = make_project(home / "projects", "p1")
    (project / "notebooks").mkdir()
    (project / "sources" / "x").mkdir(parents=True)

    monkeypatch.chdir(project)
    assert find_local_kleio_home() == str(project.resolve())

    monkeypatch.chdir(project / "notebooks")
    assert find_local_kleio_home() == str(project.resolve())

    monkeypatch.chdir(project / "sources" / "x")
    assert find_local_kleio_home() == str(project.resolve())


def test_multi_project_home_found_from_home_directories(tmp_path, monkeypatch):
    # starting at the home (or its projects/ directory) detects the home
    home = make_multi_home(tmp_path)
    make_project(home / "projects", "p1")

    monkeypatch.chdir(home)
    assert find_local_kleio_home() == str(home.resolve())

    monkeypatch.chdir(home / "projects")
    assert find_local_kleio_home() == str(home.resolve())


def test_marker_less_nested_project_keeps_legacy_behavior(tmp_path, monkeypatch):
    # a project without marker (legacy layout) inside a marked home:
    # from the project root the structural detection applies; from its
    # notebooks directory the parent is used, as before
    home = make_multi_home(tmp_path)
    project = make_project(home / "projects", "legacy", marker=False)
    (project / "notebooks").mkdir()

    monkeypatch.chdir(project)
    assert find_local_kleio_home() == str(project.resolve())

    monkeypatch.chdir(project / "notebooks")
    assert find_local_kleio_home() == str(project.resolve())


def test_invalid_project_marker_raises(tmp_path, monkeypatch):
    # a .timelink-project without a sources subdirectory is an error,
    # also when found walking up from a subdirectory
    bad = tmp_path / "bad-project"
    bad.mkdir()
    (bad / ".timelink-project").write_text("# invalid\n")
    nested = bad / "somewhere"
    nested.mkdir()

    with pytest.raises(ValueError):
        monkeypatch.chdir(nested)
        find_local_kleio_home()


def test_named_home_still_found(tmp_path, monkeypatch):
    # legacy detection by directory name still works when no markers exist
    named_home = tmp_path / "timelink-home"
    (named_home / "sources").mkdir(parents=True)
    start = tmp_path / "workdir"
    start.mkdir()

    monkeypatch.chdir(start)
    assert find_local_kleio_home() == str(named_home.resolve())


def test_fallback_to_starting_directory(tmp_path, monkeypatch):
    plain = tmp_path / "plain"
    plain.mkdir()

    monkeypatch.chdir(plain)
    assert find_local_kleio_home() == str(plain.resolve())


def test_marker_helpers_do_not_add_placeholder(tmp_path):
    # detection must not create marker files as a side effect
    project = make_project(tmp_path, "no-marker", marker=False)
    assert is_project_directory(str(project), add_placeholder=False)
    assert not (project / ".timelink-project").exists()

    home = tmp_path / "no-marker-home"
    (home / "projects").mkdir(parents=True)
    assert is_timelink_home_directory(str(home), add_placeholder=False)
    assert not (home / ".timelink-home").exists()
