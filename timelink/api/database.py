""" Database connection and setup """

import random
import string
from sqlalchemy import create_engine # pylint: disable=import-error
from sqlalchemy.orm import sessionmaker # pylint: disable=import-error
import docker # pylint: disable=import-error
import timelink.mhk.utilities as utilities

# container for postgres
postgres_container : docker.models.containers.Container = None

SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = f"postgresql://timelink:db_password@postgresserver/db"
# SQLALCHEMY_DATABASE_URL="mysql://username:password@14.41.50.12/dbname"

def is_postgres_running():
    """Check if postgres is running in docker"""
    client = docker.from_env()

    postgres_containers: list[docker.models.containers.Container]\
          = client.containers.list(filters={'ancestor': 'postgres'})
    return len(postgres_containers) > 0

# get the postgres container
def get_postgres_container()-> docker.models.containers.Container:
    """Get the postgres container
    Returns:
        docker.models.containers.Container: the postgres container
    """

    client: docker.DockerClient = docker.from_env()
    postgres_containers: docker.models.container.Container\
          = client.containers.list(filters={'ancestor': 'postgres'})
    return postgres_containers[0]


def start_postgres_server(dbpass: str | None = None, version: str | None = "latest"):
    """Starts a postgres server in docker
    Args:
        dbpass (str): database password
        version (str | None, optional): postgres version. Defaults to "latest".

    TODO: if dbpass is None, get a password from the environment
    """
    # check if postgres is already running in docker
    if is_postgres_running():
        return get_postgres_container()

    client = docker.from_env()
    psql_container = client.containers.run(
        image=f'postgres:{version}',
        detach=True,
        ports={'5432/tcp': 5432},
        environment={
            'POSTGRES_USER': 'timelink',
            'POSTGRES_PASSWORD': dbpass,
            'POSTGRES_DB': 'db'
        }
    )
    return psql_container

def random_password():
    """Generate a random password"""

    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(10))
    return result_str

# create a docker server
# get db password from MHK installation
# TODO: define method of getting db password



if "postgres" in SQLALCHEMY_DATABASE_URL:
    try:
        db_password = utilities.get_mhk_db_pwd()
    except TypeError:
      db_password = None

    if db_password is None:
      db_password = random_password()
   
    postgres_container = start_postgres_server(db_password)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
