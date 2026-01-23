"""PostgreSQL database management for Timelink.

This module provides functions to manage a PostgreSQL server running in a Docker container.
It includes utilities to check if Docker and PostgreSQL are running, retrieve PostgreSQL
container details such as user credentials and connection parameters, construct PostgreSQL
connection URLs, and start a PostgreSQL server in a Docker container with custom configuration.

Functions:
    is_postgres_running() -> bool:
        Check if PostgreSQL is running in Docker.

    get_postgres_container() -> docker.models.containers.Container:
        Get the PostgreSQL Docker container object.

    get_postgres_container_pwd() -> str:
        Get the PostgreSQL container password from environment variables.

    get_postgres_container_user() -> str:
        Get the PostgreSQL container user from environment variables.

    get_postgres_url(dbname: str) -> str:
        Construct a PostgreSQL connection URL for a given database name.

    start_postgres_server(dbname: str | None = "timelink", dbuser: str | None = "timelink",
                         dbpass: str | None = None, image: str | None = "postgres",
                         version: str | None = "latest") -> docker.models.containers.Container:
        Start a PostgreSQL server in Docker with the specified configuration.

    get_postgres_dbnames() -> list[str]:
        Get the list of non-template databases from a running PostgreSQL server.

    is_valid_postgres_db_name(db_name: str) -> bool:
        Validate a PostgreSQL database name according to PostgreSQL naming rules.
"""

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
    """Check if PostgreSQL is running in a Docker container.

    Returns:
        bool: True if at least one PostgreSQL container is running, False otherwise.

    Note:
        If Docker is not running, a warning is issued and False is returned.
    """

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
    """Get the PostgreSQL Docker container object.

    Returns:
        docker.models.containers.Container: The PostgreSQL container object.

    Raises:
        RuntimeError: If Docker is not running.
        IndexError: If no PostgreSQL container is found.
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
    """Get the PostgreSQL container password from environment variables.

    Returns:
        str: The PostgreSQL container password.

    Raises:
        RuntimeError: If Docker is not running.

    Note:
        Returns None if PostgreSQL is not running or password is not found.
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
    """Get the PostgreSQL container user from environment variables.

    Returns:
        str: The PostgreSQL container user.

    Raises:
        RuntimeError: If Docker is not running.

    Note:
        Returns None if PostgreSQL is not running or user is not found.
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
    """Construct a PostgreSQL connection URL for a given database name.

    Args:
        dbname (str): The name of the database.

    Returns:
        str: A PostgreSQL connection URL in the format:
            postgresql://user:password@localhost:5432/dbname
    """
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
    """Start a PostgreSQL server in a Docker container.

    If a PostgreSQL container is already running, returns the existing container.
    Otherwise, starts a new container with the specified configuration.

    Args:
        dbname (str, optional): Initial database name. Defaults to "timelink".
        dbuser (str, optional): Database user. Defaults to "timelink".
        dbpass (str, optional): Database password. If None, retrieves from environment.
        image (str, optional): Docker image to use. Defaults to "postgres".
        version (str, optional): Image version. Defaults to "latest".

    Returns:
        docker.models.containers.Container: The started or existing PostgreSQL container.

    Raises:
        RuntimeError: If Docker is not running or if the server fails to start/ready.
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
    """Get the list of non-template databases from a running PostgreSQL server.

    Queries the PostgreSQL system catalog to retrieve database names that:
    - Are not templates (NOT datistemplate)
    - Allow connections (datallowconn)
    - Are not the 'postgres' system database

    Returns:
        list[str]: List of database names.

    Raises:
        RuntimeError: If Docker is not running.

    Note:
        This function will start a PostgreSQL server if one is not already running.

    Example SQL query executed::

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
    """Validate a PostgreSQL database name according to PostgreSQL naming rules.

    Args:
        db_name (str): The database name to validate.

    Returns:
        bool: True if the name is valid, False otherwise.

    Note:
        A valid PostgreSQL database name must:
        - Be less than 64 characters long
        - Start with a letter or underscore
        - Contain only letters, digits, and underscores
    """
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
