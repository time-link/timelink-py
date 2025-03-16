"""
Test for the timelink.mhk.utilities module

This will only run if a file .mhk is found in the current home dir
"""
import warnings
import pytest
from pathlib import Path

from timelink.mhk.utilities import (
    get_mhk_env,
    get_mhk_app_env,
    get_dbnames,
    is_mhk_installed,
    get_mhk_info,
)
from tests import mhk_absent

if not is_mhk_installed():
    pytest.skip("skipping MHK tests (MHK not present)", allow_module_level=True)


@mhk_absent
def test_get_mhk_env_exists():
    if is_mhk_installed():
        mhk_env = get_mhk_env()
        assert mhk_env is not None, "is_mhk_installed true but no mhk_env"
        assert len(mhk_env) > 0, "could not get any values from ~.mhk"
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)


@mhk_absent
def test_is_mhk_installed():
    if Path(Path.home(), ".mhk").is_file():
        assert is_mhk_installed(), "should get a true"
    else:
        assert is_mhk_installed() is False


@mhk_absent
def test_get_mhk_env_vars_ok():
    if is_mhk_installed():
        mhk_env = get_mhk_env()
        assert mhk_env is not None, "is_mhk_installed true but no mhk_env"
        should_contain = [
            "mhk_home_dir",
            "HOST_MHK_USER_HOME",
            "HOST_MHK_HOME",
            "MYSQL_OPTS",
            "kleio_url",
            "mhk_url",
            "portainer_url",
        ]
        for v in should_contain:
            assert v in mhk_env.keys(), f'no "{v}" in  ~.mhk'
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)


@mhk_absent
def test_get_mhk_app_env_exists():
    if is_mhk_installed():
        mhk_app_env = get_mhk_app_env()
        assert mhk_app_env is not None, "is_mhk_installed true but no mhk_app_env"
        assert (
            len(mhk_app_env) > 0
        ), "could not get any values from mhk-home/app/.env"  # noqa
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)


@mhk_absent
def test_get_app_env_vars_ok():
    if is_mhk_installed():
        mhk_app_env = get_mhk_app_env()
        assert mhk_app_env is not None, "is_mhk_installed true but no mhk_app_env"
        should_contain = [
            "env_message",
            "MHK_TOMCAT_PORT",
            "MHK_KLEIO_PORT",
            "MHK_KLEIO_PORT",
            "PORTAINER_PORT",
            "MYSQL_ROOT_PASSWORD",
        ]
        for v in should_contain:
            assert v in mhk_app_env.keys(), f'no "{v}" in  ~.mhk'
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)


@mhk_absent
def test_mhk_info():
    if is_mhk_installed():
        minfo = get_mhk_info()
        assert minfo is not None, "is_mhk_installed true but no mhk_app_env"
        assert minfo.mhk_version
        assert minfo.user_home
        assert minfo.mhk_app_env
        assert minfo.mhk_home
        assert minfo.mhk_host
        assert minfo.mhk_app_env
        assert minfo.mhk_home_init
        assert minfo.mhk_home_update
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)


@mhk_absent
def test_get_dbnames():
    if is_mhk_installed():
        ns = get_dbnames()
        assert len(ns) > 0, "Could not get database names. Is Mysql running?"
    else:
        warnings.warn("MHK not installed test skipped", stacklevel=2)
