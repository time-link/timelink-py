"""
Test for the timelink.mhk.utilities module
"""
from timelink.mhk.utilities import get_mhk_env, get_mhk_app_env,get_dbnames


def test_get_mhk_env_exists():
    mhk_env = get_mhk_env()
    assert len(mhk_env) > 0, "could not get any values from ~.mhk"


def test_get_mhk_env_vars_ok():
    mhk_env = get_mhk_env()
    should_contain = ['mhk_home_dir',
                      'HOST_MHK_USER_HOME',
                      'HOST_MHK_HOME',
                      'MYSQL_OPTS',
                      'kleio_url',
                      'mhk_url',
                      'portainer_url'
                      ]
    for v in should_contain:
        assert v in mhk_env.keys(), \
            f'no "{v}" in  ~.mhk'


def test_get_mhk_app_env_exists():
    mhk_app_env = get_mhk_app_env()
    assert len(mhk_app_env) > 0, "could not get any values from ~.mhk"


def test_get_app_env_vars_ok():
    mhk_app_env = get_mhk_app_env()
    should_contain = ['env_message',
                      'MHK_TOMCAT_PORT',
                      'MHK_KLEIO_PORT',
                      'MHK_KLEIO_PORT',
                      'PORTAINER_PORT',
                      'MYSQL_ROOT_PASSWORD',
                      ]
    for v in should_contain:
        assert v in mhk_app_env.keys(), \
            f'no "{v}" in  ~.mhk'


def test_get_dbnames():
    ns = get_dbnames()
    assert len(ns) > 0, 'Could not get database names. Is Mysql running?'