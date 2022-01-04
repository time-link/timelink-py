#!/usr/bin/env python

"""Tests for `timelink-py` package."""

import pytest
from typer.testing import CliRunner

from timelink.cli import app
from tests import mhk_absent


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
