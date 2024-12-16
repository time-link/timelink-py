"""This module provides functions to manage a PostgreSQL server running in a Docker container.
It includes functions to check if Docker and PostgreSQL are running, retrieve PostgreSQL
container details such as user and password, construct a PostgreSQL URL, and start a PostgreSQL
server in a Docker container.

Functions:
- is_postgres_running: Check if PostgreSQL is running in Docker.
- get_postgres_container: Get the PostgreSQL container.
- get_postgres_container_pwd: Get the PostgreSQL container password.
- get_postgres_container_user: Get the PostgreSQL container user.
- get_postgres_url: Get the PostgreSQL URL for a given database name.
- start_postgres_server: Start a PostgreSQL server in Docker."""

import re
import time
import warnings
import logging
import docker
from sqlalchemy import create_engine, text
from timelink.api.database_utils import get_db_password
from timelink.kleio.kleio_server import is_docker_running

# container for postgres
postgres_container: docker.models.containers.Container = None

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = f"postgresql://timelink:db_password@postgresserver/db"
# SQLALCHEMY_DATABASE_URL="mysql://username:password@14.41.50.12/dbname"


def is_postgres_running():
    """Check if postgres is running in docker"""

    if not is_docker_running():
        warnings.warn("Docker is not running", stacklevel=2)
        return False

    client = docker.from_env()

    postgres_containers: list[docker.models.containers.Container] = (
        client.containers.list(filters={"ancestor": "postgres"})
    )
    return len(postgres_containers) > 0


# get the postgres container


def get_postgres_container() -> docker.models.containers.Container:
    """Get the postgres container
    Returns:
        docker.models.containers.Container: the postgres container
    """

    if not is_docker_running():
        raise RuntimeError("Docker is not running")

    client: docker.DockerClient = docker.from_env()
    postgres_containers: docker.models.container.Container = (  # pylint: disable=E1101
        client.containers.list(  # pylint: disable=E1101
            filters={"ancestor": "postgres"}
        )
    )
    return postgres_containers[0]


def get_postgres_container_pwd() -> str:
    """Get the postgres container password
    Returns:
        str: the postgres container password
    """
    if not is_docker_running():
        raise RuntimeError("Docker is not running")

    if is_postgres_running():
        container = get_postgres_container()
        pwd = [
            env
            for env in container.attrs["Config"]["Env"]
            if env.startswith("POSTGRES_PASSWORD")
        ][0].split("=")[1]
        return pwd


def get_postgres_container_user() -> str:
    """Get the postgres container user
    Returns:
        str: the postgres container user
    """
    if not is_docker_running():
        raise RuntimeError("Docker is not running")

    if is_postgres_running():
        container = get_postgres_container()
        user = [
            env
            for env in container.attrs["Config"]["Env"]
            if env.startswith("POSTGRES_USER")
        ][0].split("=")[1]
        return user


def get_postgres_url(dbname: str) -> str:
    """Get the postgres url for dbname"""
    usr = get_postgres_container_user()
    pwd = get_postgres_container_pwd()
    return f"postgresql://{usr}:{pwd}@localhost:5432/{dbname}"


def start_postgres_server(
    dbname: str | None = "timelink",
    dbuser: str | None = "timelink",
    dbpass: str | None = None,
    image: str | None = "postgres",
    version: str | None = "latest",
):
    """Starts a postgres server in docker
    Args:
        dbname (str): database name
        dbuser (str): database user
        dbpass (str): database password
        version (str | None, optional): postgres version; defaults to "latest".
    """
    if not is_docker_running():
        raise RuntimeError("Docker is not running")

    # check if postgres is already running in docker
    if is_postgres_running():
        return get_postgres_container()

    if dbname is None:
        dbname = "timelink"
    if dbuser is None:
        dbuser = "timelink"
    client = docker.from_env()
    if dbpass is None:
        dbpass = get_db_password()
    if image is None:
        image = "postgres"
    if version is None:
        version = "latest"
    psql_container = client.containers.run(
        image=f"{image}:{version}",
        detach=True,
        ports={"5432/tcp": 5432},
        environment={
            "POSTGRES_USER": dbuser,
            "POSTGRES_PASSWORD": dbpass,
            "POSTGRES_DB": dbname,
        },
    )

    timeout = 15
    stop_time = 1
    elapsed_time = 0
    # this necessary to get the status
    cont = client.containers.get(psql_container.id)
    while cont.status not in ["running"] and elapsed_time < timeout:
        time.sleep(stop_time)
        logging.debug("Waiting for postgres server to start: %s seconds", elapsed_time)
        cont = client.containers.get(psql_container.id)
        elapsed_time += stop_time
    if cont.status != "running":
        raise RuntimeError("Postgres server did not start")

    while True:
        # Execute the 'pg_isready' command in the container
        exit_code, _output = psql_container.exec_run("pg_isready")

        # If the 'pg_isready' command succeeded, break the loop
        if exit_code == 0:
            logging.info("Postgres server is ready")
            break

        # If the 'pg_isready' command failed, wait for 1 seconds and try again
        time.sleep(1)

    return psql_container


def get_postgres_dbnames():
    """Get the database names from a postgres server
    Returns:
        list[str]: list of database names

    ..code-block:: sql

        SELECT datname
            FROM pg_database
        WHERE NOT datistemplate
                AND datallowconn
                AND datname <> 'postgres';
    """

    if not is_docker_running():
        raise RuntimeError("Docker is not running")

    container = start_postgres_server()
    if container is not None:
        engine = create_engine(
            f"postgresql://{get_postgres_container_user()}:{get_postgres_container_pwd()}@localhost:5432/postgres"
        )
        with engine.connect() as conn:
            dbnames = conn.execute(
                text(
                    "SELECT datname FROM pg_database "
                    "WHERE NOT datistemplate AND datallowconn AND datname <> 'postgres';"
                )
            )
            result = [dbname[0] for dbname in dbnames]
        return result
    return []


def is_valid_postgres_db_name(db_name):
    """Check if the database name is valid"""
    # Check if the name is less than 64 characters long
    if len(db_name) >= 64:
        return False

    # Check if the name starts with a letter or underscore
    if not re.match(r"^[a-zA-Z_]", db_name):
        return False

    # Check if the name contains only letters, digits, and underscores
    if not re.match(r"^\w+$", db_name):
        return False

    # If all checks pass, the name is valid
    return True
