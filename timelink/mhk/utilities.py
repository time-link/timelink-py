"""
Utilities for interaction with and MHK installation.
MHK is the name of Java Webapp that preceded Timelink.

(c) Joaquim Carvalho, 2021. MIT Licence.

"""
import os
from typing import Type, Union

from dotenv import dotenv_values
from sqlalchemy import create_engine, text


def get_mhk_env() -> Type[Union[str, None]]:
    """
    Get the MHK environment variables from ~/.mhk

    The .mhk file contains the path for the mhk-home of the
    current user. It is created by the MHK install process.
    """
    home_dir = os.getenv('HOME')
    if home_dir is None:
        return {}
    else:
        return dotenv_values(home_dir + "/.mhk")


def get_mhk_app_env():
    """
    Get the mhk app environment variables from mhk-home/app/.env

    The .env filed contains information used by docker to create the
    MHK application and some running options, like header color and
    docker image tags used for updates.

    The .env file is created by the MHK installation process.
    Its contents can be changed my mhk manager commands.
    """
    mhk_env = get_mhk_env()
    mhk_home_dir = mhk_env['HOST_MHK_HOME']
    if mhk_home_dir is not None:
        app_env = dotenv_values(mhk_home_dir + '/app/.env')
        return app_env
    return {}


def get_connection_string(db: str, host='localhost', port='3307'):
    pwd = get_db_pwd()
    conn_string = f'mysql+mysqlconnector://root:{pwd}@{host}:{port}/{db}'
    return conn_string


def get_engine(db: str, host='localhost', port='3307', echo=False):
    cs = get_connection_string(db, host, port)
    return create_engine(cs, echo=echo, future=True)


def get_dbnames():
    """
    Get the names of MHK databases in MySQL

    A search is made in the MySQL server running in the local host port 3307
    """
    pwd = get_db_pwd()
    conn_string = \
        'mysql+mysqlconnector://root:{p}@localhost:3307/mysql'.format(p=pwd)
    mysql = create_engine(conn_string, echo=False, future=True)
    with mysql.connect() as conn:
        databases = conn.execute(text(
            "SELECT table_schema FROM information_schema.tables"
            "       WHERE  table_name = 'entities'"))
        result = [db[0] for db in databases]
    return result


def get_db_pwd():
    """
    Get the password of the database from the MHL environment
    """
    app_env = get_mhk_app_env()
    pwd = app_env['MYSQL_ROOT_PASSWORD']
    if pwd is None:
        raise TypeError(
            "Could not find MHK database password."
            "Is MHK installed?")
    else:
        return pwd
