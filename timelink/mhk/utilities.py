"""
Utilities for interaction with and MHK installation.
MHK is the name of Java Webapp that preceded Timelink.

(c) Joaquim Carvalho, 2021. MIT Licence.

"""
import os
from dotenv import dotenv_values
from sqlalchemy import create_engine, text


def get_mhk_env():
    """
    Get the MHK environment variables from ~/.mhk

    The .mhk file contains the path for the mhk-home of the
    current user. It is created by the MHK install process.
    """
    home_dir = os.getenv('HOME')
    print("home  : " + home_dir)
    result = dotenv_values(home_dir + "/.mhk")
    return result


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
    app_env = dotenv_values(mhk_home_dir + '/app/.env')
    return app_env


def get_dbnames():
    """
    Get the names of MHK databases in MySQL

    A search is made in the MySQL server running in the local host port 3307
    """
    app_env = get_mhk_app_env()
    pwd = app_env['MYSQL_ROOT_PASSWORD']
    conn_string = \
        'mysql+mysqlconnector://root:{p}@localhost:3307/mysql'.format(p=pwd)
    mysql = create_engine(conn_string, echo=False, future=True)
    with mysql.connect() as conn:
        databases = conn.execute(text(
            "SELECT table_schema FROM information_schema.tables"
            "       WHERE  table_name = 'entities'"))
        result = [db[0] for db in databases]
    return result


