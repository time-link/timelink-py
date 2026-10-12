"""Tests for the ``timelink create project`` and ``timelink create multiproject``
commands.

The git commands are faked: "git clone" copies a local template directory,
so no network access is needed.
"""

import shutil
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from timelink import cli

runner = CliRunner()


def make_template(parent: Path, marker: str, subdirs: list) -> Path:
    """A local fake of a template repository, including a .git directory
    with a recognizable file that must be discarded by create."""
    template = parent / "template-repo"
    for sub in subdirs:
        (template / sub).mkdir(parents=True)
    (template / marker).write_text("# marker\n")
    (template / ".git").mkdir()
    (template / ".git" / "from-template-repo").write_text("template history")
    return template


def fake_git_run_factory(template: Path):
    """Return a subprocess.run replacement where "git clone" copies the
    local template and "git init" is a no op."""

    def fake_run(args, **kwargs):
        if args[:2] == ["git", "clone"]:
            shutil.copytree(template, Path(args[-1]))
        elif args[:2] == ["git", "init"]:
            (Path(kwargs["cwd"]) / ".git").mkdir()
        return subprocess.CompletedProcess(args, 0)

    return fake_run


def test_create_project(tmp_path, monkeypatch):
    template = make_template(tmp_path, ".timelink-project", ["sources", "notebooks"])
    monkeypatch.setattr(cli.subprocess, "run", fake_git_run_factory(template))
    target = tmp_path / "new-project"

    result = runner.invoke(cli.app, ["create", "project", str(target)])

    assert result.exit_code == 0, result.output
    assert (target / "sources").is_dir()
    # marker present and template repository history discarded
    assert (target / ".timelink-project").is_file()
    assert not (target / ".git" / "from-template-repo").exists()


def test_create_project_adds_missing_marker(tmp_path, monkeypatch):
    # an old template without marker: the marker must be added
    template = make_template(tmp_path, ".unused", ["sources"])
    monkeypatch.setattr(cli.subprocess, "run", fake_git_run_factory(template))
    target = tmp_path / "new-project"

    result = runner.invoke(cli.app, ["create", "project", str(target)])

    assert result.exit_code == 0, result.output
    assert (target / ".timelink-project").is_file()


def test_create_multiproject(tmp_path, monkeypatch):
    template = make_template(tmp_path, ".timelink-home", ["projects", "system"])
    monkeypatch.setattr(cli.subprocess, "run", fake_git_run_factory(template))
    target = tmp_path / "new-multi"

    result = runner.invoke(cli.app, ["create", "multiproject", str(target)])

    assert result.exit_code == 0, result.output
    assert (target / "projects").is_dir()
    assert (target / ".timelink-home").is_file()


def test_create_refuses_non_empty_directory(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("git must not be called for an existing directory")

    monkeypatch.setattr(cli.subprocess, "run", fail_if_called)
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "data.txt").write_text("user data")

    result = runner.invoke(cli.app, ["create", "project", str(target)])

    assert result.exit_code == 1
    # user data untouched
    assert (target / "data.txt").read_text() == "user data"


def test_create_removes_partial_directory_on_clone_failure(tmp_path, monkeypatch):
    def failing_run(args, **kwargs):
        if args[:2] == ["git", "clone"]:
            # a partial clone left behind by a failed git
            target = Path(args[-1])
            target.mkdir()
            (target / "partial").write_text("partial")
            raise subprocess.CalledProcessError(128, args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(cli.subprocess, "run", failing_run)
    target = tmp_path / "broken"

    result = runner.invoke(cli.app, ["create", "project", str(target)])

    assert result.exit_code == 1
    assert not target.exists()


def test_create_rejects_invalid_template(tmp_path, monkeypatch):
    # template without sources: not a valid project directory
    template = make_template(tmp_path, ".timelink-project", ["not-sources"])
    monkeypatch.setattr(cli.subprocess, "run", fake_git_run_factory(template))
    target = tmp_path / "invalid"

    result = runner.invoke(cli.app, ["create", "project", str(target)])

    assert result.exit_code == 1
    assert not target.exists()
