#!/usr/bin/env python

"""Tests for `timelink-py` package."""

import random
import pytest
from typer.testing import CliRunner
from timelink.cli import app, create_db_index, avoid_db_patterns
from tests import mhk_absent, TEST_DIR, skip_on_travis


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Timelink and MHK manager" in result.output


@mhk_absent
def test_command_mhk_version():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(app, ["mhk", "version"])
    print(f"Test result {result.exit_code}")
    # assert result.exit_code == 0
    assert "Portainer URL" in result.output or "not found" in result.output


@mhk_absent
def test_command_mhk_status():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(app, ["mhk", "status"])
    assert result.exit_code == 0
    assert "Stopped" in result.output


# test db command
@skip_on_travis
def test_db_list():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(app, ["db", "list"])
    assert result.exit_code == 0

@skip_on_travis
def test_db_current():
    """Test the CLI."""
    runner = CliRunner()
    db_list = create_db_index(avoid_patterns=avoid_db_patterns)
    # chose a random key from dict db_list
    db_key = list(db_list.keys())[random.randint(0, len(db_list) - 1)]
    print(f"db_key: {db_key} db_list: {db_list[db_key]}")
    result = runner.invoke(app, ["db", "current", str(db_key)])
    print(f"Test result {result.exit_code}")
    print(f"Test result {result.stdout}")
    assert result.exit_code == 0

@skip_on_travis
def test_db_upgrade():
    """Test the CLI."""
    runner = CliRunner()
    db_list = create_db_index(avoid_patterns=avoid_db_patterns)
    # chose a random key from dict db_list
    db_key = list(db_list.keys())[random.randint(0, len(db_list) - 1)]
    #
    db_key = 17
    print(f"db_key: {db_key} db_list: {db_list[db_key]}")
    result = runner.invoke(app, ["db", "upgrade", str(db_key)])
    print(f"Test result {result.exit_code}")
    print(f"Test result {result.stdout}")
    assert result.exit_code == 0

@skip_on_travis
def test_db_heads():
    runner = CliRunner()
    db_list = create_db_index(avoid_patterns=avoid_db_patterns)
    # choose a random db
    db_key = list(db_list.keys())[random.randint(0, len(db_list) - 1)]
    print(f"db_key: {db_key} db_list: {db_list[db_key]}")
    heads = runner.invoke(app, ["db", "heads", str(db_key)])
    print(heads)

@skip_on_travis
def test_create_db():
    runner = CliRunner()
    result = runner.invoke(app, ["db", "create", f"sqlite:///{TEST_DIR}/db/test.db"])
    print(f"Test result {result.exit_code}")
    print(f"Test result {result.stdout}")
    assert result.exit_code == 0
    assert "created" in result.output
    # assert "not found" in result.output
    # assert "Error" in result.output
    # assert "Exception" in result.output
    # assert "Traceback" in result.output
    # assert "Usage" in result.output


def test_get_latest_version():
    from timelink import get_latest_version
    version = get_latest_version()
    print(f"Latest version: {version}")
    assert version is not None
    assert len(version) > 0

