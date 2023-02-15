from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import docker
from timelink.mhk.utilities import get_db_pwd
from .models.base_class import Base

# container for postgres
postgres_container : docker.models.containers.Container = None



# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
SQLALCHEMY_DATABASE_URL = f"postgresql://timelink:db_password@postgresserver/db"
# SQLALCHEMY_DATABASE_URL="mysql://username:password@14.41.50.12/dbname"

def is_postgres_running():
    """Check if postgres is running in docker"""
    client = docker.from_env()
    postgres_container = client.containers.list(filters={'ancestor': 'postgres'})
    return len(postgres_container) > 0

# get the postgres container
def get_postgres_container()-> docker.models.containers.Container:
    """Get the postgres container
    Returns:
        docker.models.containers.Container: the postgres container
    """
    client = docker.from_env()
    postgres_container = client.containers.list(filters={'ancestor': 'postgres'})
    return postgres_container[0]


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

# create a docker server
# get db password from MHK installation
# TODO: define method of getting db password
db_password = get_db_pwd()
postgres_container = start_postgres_server(db_password)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

