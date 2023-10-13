"""
Utilities for interaction with and MHK installation.

MHK is the name of Java Webapp that preceded Timelink.

(c) Joaquim Carvalho, 2021. MIT Licence.

"""

import warnings
from collections import namedtuple
from configparser import ConfigParser
from pathlib import Path
from typing import Type, Union

from sqlalchemy import create_engine, text


def get_env_as_dict(filename: str) -> dict:
    """
    Reads environment variables from a file and return a SafeConfig object

    Rationale: SafeConfig parser requires
    :param filename: Name of a file
    :return:
    """
    conf = "[env]\n"
    with open(filename, "r") as f:
        env_file = f.read()  # read from file
        conf = conf + env_file

    env = ConfigParser()
    # preserve case in env vars
    # see https://stackoverflow.com/questions/1611799/preserve-case-in-configparser # noqa: E501
    env.optionxform = str

    env.read_string(conf)

    return remove_quotes(dict(env["env"].items()))


def remove_quotes(original):
    """
    Removes quotes from quoted values in env variables
    See https://stackoverflow.com/a/50772706
    :param original: dict with env variables
    :return: copy of the dict with the values unquoted
    """
    d = original.copy()
    for key, value in d.items():
        if isinstance(value, str):
            s = d[key]
            if s.startswith(('"', "'")):
                s = s[1:]
            if s.endswith(('"', "'")):
                s = s[:-1]
            d[key] = s
            # print(f"string found: {s}")
        if isinstance(value, dict):
            d[key] = remove_quotes(value)
    #
    return d


def get_mhk_env() -> Type[Union[str, None]]:
    """
    Get the MHK environment variables from ~/.mhk

    The .mhk file contains the path for the mhk-home of the
    current user. It is created by the MHK install process.
    """
    if is_mhk_installed():
        home_dir = str(Path.home())
        if home_dir is None:
            warnings.warn("Could not get a home directory", stacklevel=2)
            return None
        else:
            env = get_env_as_dict(home_dir + "/.mhk")
            if env is None:
                warnings.warn("Could not read .mhk env from user home", stacklevel=2)
            return env
    else:
        warnings.warn("MHK is not installed", stacklevel=2)
        return None


def get_mhk_app_env() -> Type[Union[str, None]]:
    """
    Get the mhk app environment variables from mhk-home/app/.env

    The .env filed contains information used by docker to create the
    MHK application and some running options, like header color and
    docker image tags used for updates.

    The .env file is created by the MHK installation process.
    Its contents can be changed my mhk manager commands.
    """
    mhk_env = get_mhk_env()
    if mhk_env is not None:
        mhk_home_dir = mhk_env["HOST_MHK_HOME"]
        app_env = get_env_as_dict(mhk_home_dir + "/app/.env")
        return app_env
    else:
        warnings.warn("Could not get MHK env variables", stacklevel=2)
        return None


def get_db_pwd() -> str:
    """
    Get the password of the database from the MHK environment
    """
    app_env = get_mhk_app_env()
    if app_env:
        pwd = app_env["MYSQL_ROOT_PASSWORD"]
        if pwd is None:
            raise TypeError("Could not find MHK database password." "Is MHK installed?")
        else:
            return pwd
    else:
        raise TypeError(
            "Could not find MHK app information." "Is MHK installed?"
        )  # noqa: E501


def get_connection_string(db: str, host="localhost", port="3307") -> str:
    pwd = get_db_pwd()
    conn_string = f"mysql+mysqlconnector://root:{pwd}@{host}:{port}/{db}"
    return conn_string


def get_engine(db: str, host="localhost", port="3307", echo=False):
    cs = get_connection_string(db, host, port)
    return create_engine(cs, echo=echo, future=True)


def get_dbnames():
    """
    Get the names of MHK databases in MySQL

    A search is made in the MySQL server running in the local host port 3307
    """
    pwd = get_mhk_db_pwd()
    conn_string = "mysql+mysqlconnector://root:{p}@localhost:3307/mysql".format(p=pwd)
    mysql = create_engine(conn_string, echo=False, future=True)
    with mysql.connect() as conn:
        databases = conn.execute(
            text(
                "SELECT table_schema FROM information_schema.tables"
                "       WHERE  table_name = 'entities'"
            )
        )
        result = [db[0] for db in databases]
    return result


def get_mhk_db_pwd():
    """
    Get the password of the database from the MHK environment
    """
    app_env = get_mhk_app_env()
    if app_env:
        pwd = app_env["MYSQL_ROOT_PASSWORD"]
        if pwd is None:
            raise TypeError("Could not find MHK database password." "Is MHK installed?")
        else:
            return pwd
    else:
        raise TypeError("Could not find MHK app information." "Is MHK installed?")


def get_mhk_info():
    mhk_env = get_mhk_env()
    user_home = mhk_env["HOST_MHK_USER_HOME"]
    mhk_home = mhk_env["HOST_MHK_HOME"]
    with open(mhk_home + "/app/manager_version", "r") as file:
        mv = file.read().replace("\n", "")
    with open(mhk_home + "/.mhk-home", "r") as file:
        mhk_home_update = file.read().replace("\n", "")
    with open(mhk_home + "/.mhk-home-manager-init", "r") as file:
        mhk_home_init = file.read().replace("\n", "")
    mhk_app_env = get_mhk_app_env()
    mhk_host = mhk_app_env.get("MHK_HOST", "localhost")

    MHKInfo = namedtuple(
        "MHKInfo",
        [
            "mhk_app_env",
            "mhk_home",
            "mhk_home_init",
            "mhk_home_update",
            "mhk_host",
            "mhk_version",
            "user_home",
        ],
    )
    mhk_info = MHKInfo(
        mhk_app_env, mhk_home, mhk_home_init, mhk_home_update, mhk_host, mv, user_home
    )
    return mhk_info


def is_mhk_installed() -> bool:
    """Returns true if a MHK instalation is found

    Checks the existence of ~/.mhk
    """
    return Path(Path.home(), ".mhk").is_file()
