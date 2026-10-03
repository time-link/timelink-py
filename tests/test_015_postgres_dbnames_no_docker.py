"""Tests for database listing when Docker is not running.

`timelink db list` and the webapp/notebook helpers must not require Docker:
when it is not running, PostgreSQL databases are simply not listed (a
warning is issued) and SQLite databases are still shown. Docker is faked
out with monkeypatch so these tests run in any environment.
"""

import warnings

import pytest

import timelink.api.database_postgres as database_postgres
from timelink.api.database import get_postgres_dbnames


@pytest.fixture
def docker_down(monkeypatch):
    """Simulate Docker not running."""
    monkeypatch.setattr(database_postgres, "is_docker_running", lambda: False)


def test_get_postgres_dbnames_empty_when_docker_down(docker_down):
    """Listing postgres db names must warn and return [], not raise."""
    with pytest.warns(UserWarning, match="Docker is not running"):
        dbnames = get_postgres_dbnames()
    assert dbnames == []


def test_create_db_index_without_docker(docker_down, tmp_path, monkeypatch):
    """`timelink db list` index: sqlite databases still listed without Docker."""
    from timelink import cli

    (tmp_path / "a_database.sqlite").touch()
    monkeypatch.setattr(cli, "current_working_directory", str(tmp_path))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        db_index = cli.create_db_index(avoid_patterns=cli.avoid_db_patterns)

    assert db_index, "the sqlite database should be listed"
    assert all(db[0] == "sqlite" for db in db_index.values())
