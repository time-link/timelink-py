""" Database connection and setup 

TODO
    - migrate postgres functions to TimelinkDatabase
    - create metadata and engine in TimelinkDatabase
    - create tables in TimelinkDatabase
    - create database classes in TimelinkDatabase
    - create mappings in TimelinkDatabase
    - use logging to database functions.

"""
import os
import random
import string
from sqlalchemy import create_engine, inspect, select, text  # pylint: disable=import-error
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy_utils import database_exists, create_database  # pylint: disable=import-error
import docker  # pylint: disable=import-error
from timelink.mhk import utilities
from timelink.api import models  # pylint: disable=unused-import
from timelink.api.models import PomSomMapper, pom_som_base_mappings


# container for postgres
postgres_container: docker.models.containers.Container = None

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = f"postgresql://timelink:db_password@postgresserver/db"
# SQLALCHEMY_DATABASE_URL="mysql://username:password@14.41.50.12/dbname"


def is_postgres_running():
    """Check if postgres is running in docker"""
    client = docker.from_env()

    postgres_containers: list[docker.models.containers.Container]\
        = client.containers.list(filters={'ancestor': 'postgres'})
    return len(postgres_containers) > 0

# get the postgres container


def get_postgres_container() -> docker.models.containers.Container:
    """Get the postgres container
    Returns:
        docker.models.containers.Container: the postgres container
    """

    client: docker.DockerClient = docker.from_env()
    postgres_containers: docker.models.container.Container\
        = client.containers.list(filters={'ancestor': 'postgres'})
    return postgres_containers[0]

def get_postgres_container_pwd() -> str:
    """Get the postgres container password
    Returns:
        str: the postgres container password
    """
    if is_postgres_running():
        container = get_postgres_container()
        pwd = [env for env in container.attrs['Config']['Env'] 
            if env.startswith('POSTGRES_PASSWORD')][0].split('=')[1]
        return pwd

def start_postgres_server(dbname: str | None = 'timelink',
                          dbuser: str | None = 'timelink',
                          dbpass: str | None = None,
                          version: str | None = "latest"):
    """Starts a postgres server in docker
    Args:
        dbname (str): database name
        dbuser (str): database user
        dbpass (str): database password
        version (str | None, optional): postgres version. Defaults to "latest".

    TODO: if dbpass is None, get a password from the environment
    """
    # check if postgres is already running in docker
    if is_postgres_running():
        return get_postgres_container()

    client = docker.from_env()
    if dbpass is None:
        dbpass = get_db_password()
    psql_container = client.containers.run(
        image=f'postgres:{version}',
        detach=True,
        ports={'5432/tcp': 5432},
        environment={
            'POSTGRES_USER': dbuser,
            'POSTGRES_PASSWORD': dbpass,
            'POSTGRES_DB': dbname
        }
    )
    return psql_container


def random_password():
    """Generate a random password"""

    letters = string.ascii_letters
    result_str = ''.join(random.choice(letters) for i in range(10))
    return result_str


def get_db_password():
    # get password from environment
    db_passord = os.environ.get('TIMELINK_DB_PASSWORD')
    if db_passord is None:
        db_passord = random_password()
        os.environ['TIMELINK_DB_PASSWORD'] = db_passord
    return db_passord


def get_dbnames():
    """Get the database names
    Returns:
        list[str]: list of database names
    
    SELECT datname
        FROM pg_database
    WHERE NOT datistemplate
            AND datallowconn
            AND datname <> 'postgres';
    """
    start_postgres_server()
    if is_postgres_running():
        container = get_postgres_container()
        engine = create_engine(f'postgresql://postgres:{get_postgres_container_pwd()}@localhost:5432/postgres')
        with engine.connect() as conn:
            dbnames = conn.execute(
                text(
                    "SELECT datname FROM pg_database WHERE NOT datistemplate AND datallowconn AND datname <> 'postgres';")
                    )
            result = [dbname[0] for dbname in dbnames]
        return result
    else:
        return []
    
class TimelinkDatabase:
    """Database connection and setup

    Creates a database connection and session. If the database does not exist,
      it is created.
    db_type determines the type of database. 

    Currently, only sqlite, postgres, and mysql are supported.

    If db_type is sqlite, the database is created in the current directory. 
    If db_type is postgres or mysql,
    the database is created in a docker container. 
    If the database is postgres, the container is named
    timelink-postgres. 
    If the database is mysql, the container is named timelink-mysql.

    Args:
        db_name (str, optional): database name. Defaults to "timelink".
        db_type (str, optional): database type. Defaults to "sqlite".
        db_url (str, optional): database url. If None, a url is generated. Defaults to None
        db_user (str, optional): database user. Defaults to None.
        db_pwd (str, optional): database password. Defaults to None.
        connect_args (dict, optional): database connection arguments. Defaults to None.

    Fields:
        db_url (str): database url
        db_name (str): database name
        db_user (str): database user
        db_pwd (str): database password
        engine (Engine): database engine
        session (Session): database session factory
        metadata (MetaData): database metadata
        db_container: database container

    Example:
        db = TimelinkDatabase('timelink', 'sqlite')
        with db.session() as session:
            # do something with the session
    """

    def __init__(self,
                 db_name: str = "timelink",
                 db_type: str = "sqlite",
                 db_url=None,
                 db_user=None,
                 db_pwd=None,
                 **connect_args):
        """Initialize the database connection and setup"""
        if db_url is not None:
            self.db_url = db_url
        else:
            if db_type == "sqlite":
                if db_name == ':memory:':
                    self.db_url = "sqlite:///:memory:"
                else:
                    self.db_url = f"sqlite:///./{db_name}.sqlite"
                # TODO: allow for path to be specified
                connect_args = {"check_same_thread": False}
            elif db_type == "postgres":
                # TODO Start a postgres server in docker
                if db_pwd is None:
                    self.db_pwd = get_db_password()
                else:
                    self.db_pwd = db_pwd
                if db_user is None:
                    self.db_user = "postgres"
                else:
                    self.db_user = db_user
                self.db_url = f"postgresql://{self.db_user}:{self.db_pwd}@127.0.0.1/{db_name}"
                self.db_container = start_postgres_server(
                    db_name, self.db_user, self.db_pwd)
                self.db_pwd = get_postgres_container_pwd()
            elif db_type == "mysql":
                self.db_url = f"mysql://{db_user}:{db_pwd}@localhost/{db_name}"
                if db_pwd is None:
                    try:
                        self.db_pwd = utilities.get_mhk_db_pwd()
                    except TypeError:
                        self.db_pwd = None
                if db_pwd is None:
                    self.db_pwd = random_password()
                # TODO Start a mysql server in docker
            else:
                raise ValueError(f"Unknown database type: {db_type}")

        self.engine = create_engine(self.db_url, connect_args=connect_args)
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.metadata = models.Base.metadata
        self.create_tables()
        with self.session() as session:
            session.commit()
            session.rollback()
            self.load_database_classes(session)
            self.ensure_all_mappings(session)

    def create_tables(self):
        """Creates the tables from the current ORM metadata if needed

        :return: None
        """
        self.metadata.create_all(self.engine)  # only creates if missing

    def table_names(self):
        """Current tables in the database"""
        insp = inspect(self.engine)
        db_tables = insp.get_table_names()  # tables in the database
        return db_tables

    def load_database_classes(self, session):
        """
        Populates database with core Database classes
        :param session:
        :return:
        """

        # Check if the core tables are there
        existing_tables = self.table_names()
        base_tables = [v[0].table_name for v in pom_som_base_mappings.values()]
        missing = set(base_tables) - set(existing_tables)
        if len(missing) > 0:
            self.create_tables()

        # check if we have the data for the core database entity classes
        stmt = select(PomSomMapper.id)
        available_mappings = session.execute(stmt).scalars().all()
        for k in pom_som_base_mappings.keys():  # pylint: disable=consider-iterating-dictionary
            if k not in available_mappings:
                data = pom_som_base_mappings[k]
                session.bulk_save_objects(data)
        # this will cache the pomsom mapper objects
        session.commit()

    def ensure_all_mappings(self, session):
        """Ensure that all database classes have a table and ORM class"""
        pom_classes = PomSomMapper.get_pom_classes(session)
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session)

    def __enter__(self):
        return self.session()

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_db(self):
        """Get a database session
        Returns:
            Session: database session
        """
        db = self.session()
        try:
            yield db
        finally:
            db.close()

    def get_engine(self):
        """Get the database engine
        Returns:
            Engine: database engine
        """
        return self.engine
    
    def get_metadata(self):
        """Get the database metadata
        Returns:
            MetaData: database metadata
        """
        return self.metadata

    def drop_db(self, session):
        """
        This will drop all timelink related tables from the database.
        It will not touch non timelink tables that might exist.
        :param session:
        :return:
        """
        session.rollback()
        self.load_database_classes(session)
        self.ensure_all_mappings(session)
        session.commit()
        session.close()
        self.metadata = models.Base.metadata
        self.metadata.drop_all(self.engine)
