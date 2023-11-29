""" Database connection and setup 

TODO
    - migrate postgres functions to TimelinkDatabase
    - use logging to database functions.

"""
from datetime import timezone
import os
import random
import string
import time
from typing import List
import warnings
from sqlalchemy import Engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.sql import table # pylint: disable=import-error see https://github.com/sqlalchemy/sqlalchemy/wiki/Views
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import create_database
import docker  # pylint: disable=import-error
from timelink.mhk import utilities
from timelink.api import models  # pylint: disable=unused-import
from timelink.api.models import Entity, PomSomMapper
from timelink.api.models import pom_som_base_mappings
from timelink.api.models import Person
from timelink.api.models import Attribute
from timelink.api.models import KleioImportedFile
from timelink.kleio import KleioFile, KleioServer, import_status_enum
from . import views

# container for postgres
postgres_container: docker.models.containers.Container = None

# SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
# SQLALCHEMY_DATABASE_URL = f"postgresql://timelink:db_password@postgresserver/db"
# SQLALCHEMY_DATABASE_URL="mysql://username:password@14.41.50.12/dbname"

def is_postgres_running():
    """Check if postgres is running in docker"""
    client = docker.from_env()

    postgres_containers: list[
        docker.models.containers.Container
    ] = client.containers.list(filters={"ancestor": "postgres"})
    return len(postgres_containers) > 0


# get the postgres container


def get_postgres_container() -> docker.models.containers.Container:
    """Get the postgres container
    Returns:
        docker.models.containers.Container: the postgres container
    """

    client: docker.DockerClient = docker.from_env()
    postgres_containers: docker.models.container.Container = client.containers.list(
        filters={"ancestor": "postgres"}
    )
    return postgres_containers[0]


def get_postgres_container_pwd() -> str:
    """Get the postgres container password
    Returns:
        str: the postgres container password
    """
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
    if is_postgres_running():
        container = get_postgres_container()
        user = [
            env
            for env in container.attrs["Config"]["Env"]
            if env.startswith("POSTGRES_USER")
        ][0].split("=")[1]
        return user


def start_postgres_server(
    dbname: str | None = "timelink",
    dbuser: str | None = "timelink",
    dbpass: str | None = None,
    version: str | None = "latest",
):
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
        image=f"postgres:{version}",
        detach=True,
        ports={"5432/tcp": 5432},
        environment={
            "POSTGRES_USER": dbuser,
            "POSTGRES_PASSWORD": dbpass,
            "POSTGRES_DB": dbname,
        },
    )
    # wait for the container to start
    psql_container.reload()
    while psql_container.status != "running":
        psql_container.reload()
        # wait one second
        time.sleep(1)
    return psql_container


def random_password():
    """Generate a random password"""

    letters = string.ascii_letters
    result_str = "".join(random.choice(letters) for i in range(10))
    return result_str


def get_db_password():
    # get password from environment
    db_passord = os.environ.get("TIMELINK_DB_PASSWORD")
    if db_passord is None:
        db_passord = random_password()
        os.environ["TIMELINK_DB_PASSWORD"] = db_passord
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

    TODO: equivalent in sqlLite and mysql
    """
    
    container = get_postgres_container()
    if container is not None:
        engine = create_engine(
            f"postgresql://{get_postgres_container_user()}:{get_postgres_container_pwd()}@localhost:5432"
        )
        with engine.connect() as conn:
            dbnames = conn.execute(
                text(
                    "SELECT datname FROM pg_database WHERE NOT datistemplate AND datallowconn AND datname <> 'postgres';"
                )
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

    db_url: str
    db_name: str
    db_user: str
    db_pwd: str
    db_type: str
    nattributes: Table | None = None
    nfuncs: Table | None = None

    def __init__(
        self,
        db_name: str = "timelink",
        db_type: str = "sqlite",
        db_url=None,
        db_user=None,
        db_pwd=None,
        db_path=None,
        **connect_args,
    ):
        """Initialize the database connection and setup
        
        Args:
            db_name (str, optional): database name. Defaults to "timelink".
            db_type (str, optional): database type. Defaults to "sqlite".
            db_url (str, optional): database url. If None, a url is generated. Defaults to None
            db_user (str, optional): database user. Defaults to None.
            db_pwd (str, optional): database password. Defaults to None.
            db_path (str, optional): database path (for sqlite databases). Defaults to None.
            connect_args (dict, optional): SQLAlchemy database connection arguments. Defaults to None.
                        
        """
        if db_url is not None:
            self.db_url = db_url
        else:
            if db_type == "sqlite":
                if db_name == ":memory:":
                    self.db_url = "sqlite:///:memory:"
                else:
                    if db_path is None:
                        db_path = os.getcwd()
                    if connect_args is None:
                        connect_args = {"check_same_thread": False}
                    db_path = os.path.abspath(db_path) 
                    os.makedirs(db_path, exist_ok=True)
                    self.db_url = f"sqlite:///{db_path}/{db_name}.sqlite"
            elif db_type == "postgres":
                if db_pwd is None:
                    self.db_pwd = get_db_password()
                else:
                    self.db_pwd = db_pwd
                if db_user is None:
                    self.db_user = "postgres"
                else:
                    self.db_user = db_user
                if is_postgres_running():
                    self.db_container = get_postgres_container()
                    # if it it is running, we need the password
                    container_vars = self.db_container.attrs["Config"]["Env"]
                    pwd = [var for var in container_vars if "POSTGRES_PASSWORD" in var][
                        0
                    ]
                    self.db_pwd = pwd.split("=")[1]
                else:
                    self.db_container = start_postgres_server(
                        db_name, self.db_user, self.db_pwd
                    )
                self.db_url = (
                    f"postgresql://{self.db_user}:{self.db_pwd}@127.0.0.1/{db_name}"
                )
                self.db_container = start_postgres_server(
                    db_name, self.db_user, self.db_pwd
                )
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

    def create_views(self):
        """Creates the views 


        :return: None
        """
        self.nattributes = self.get_nattribute_view()

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
        for (
            k
        ) in (
            pom_som_base_mappings.keys()
        ):  # pylint: disable=consider-iterating-dictionary
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
        self.session().close()

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
        try:
            with self.engine.begin() as con:
                self.metadata.drop_all(con)
        except Exception as exc:
            warnings.warn("Dropping tables problem " + str(exc), stacklevel=2)

    def get_imported_files(self):
        """Returns the list of imported files"""
        return self.session().query(KleioImportedFile).all()
    
    def get_import_status(self, kleio_files: List[KleioFile], match_path=False) -> List[KleioFile]:
        """Get the import status of the kleio files

        The status in returned in KleioFile.import_status

        Args:
            kleio_files (List[KleioFile]): list of kleio files with extra field import_status
            match_path (bool, optional): if True, match the path of the kleio file with the path of the imported file. Defaults to False.

        Returns:
            List[KleioFile]: list of kleio files with field import_status
        """
        return get_import_status(self, kleio_files, match_path)

    def query(self, query_spec):
        """ Executes a query in the database
        
        Args:
            query: sqlAlchemy query"""
        
        with self.session() as session:
            result = session.query(query_spec)
        return result
    
    def get_models_ids(self):
        """Get the ORM model classes as a list of ids

        Returns:
            list: list of ORM classes as string ids
        """
        return Entity.get_som_mapper_ids()
    

    def get_model(self, class_id: str): 
        """Get the ORM class for a entity type

        Returns:
            ORM class
        """
        return Entity.get_orm_for_pom_class(class_id)


    def get_nattribute_view(self):
        """ Return the nattribute view.

        Returns a sqlalchemy table linked to the nattributes view of timelink/MHK databases
        This views joins the table "persons" and the table "attributes" providing attribute
        values with person names and sex.

        The column id contains the id of the person/object, not of the attribute

        Returns:
                A table object with the nattribute view
        """

        # TODO View creation should go to timelink-py
        nattribute_sql = """
            SELECT p.id        AS id,
                p.name      AS name,
                p.sex       AS sex,
                a.the_type  AS the_type,
                a.the_value AS the_value,
                a.the_date  AS the_date,
                p.obs       AS pobs,
                a.obs       AS aobs
            FROM attributes a, persons p
            WHERE (a.entity = p.id)
            """
        if self.nattributes is None:
            eng: Engine = self.engine
            metadata: MetaData = self.metadata
            texists = inspect(eng).has_table('nattributes')
            
            person = Person.__table__
            attribute = Attribute.__table__
            attr = views.view(
                "nattributes", metadata, 
                select(
                    person.c.id.label("id"),
                    person.c.name.label("name"),
                    person.c.sex.label("sex"),
                    attribute.c.the_type.label("the_type"),
                    attribute.c.the_value.label("the_value"),
                    attribute.c.the_date.label("the_date"),
                    person.c.obs.label("pobs"),
                    attribute.c.obs.label("aobs")
                ).select_from(person.join(attribute, person.c.id == attribute.c.entity))
            )
            self.nattributes = attr
            with eng.begin() as con:
                metadata.create_all(con)  
        return self.nattributes   


def get_import_status(db: TimelinkDatabase, kleio_files: List[KleioFile], match_path=False) -> List[KleioFile]:
    """Get the import status of the kleio files

        The status in returned in KleioFile.import_status

            I = "I" # imported
            E = "E" # imported with error
            W = "W" # imported with warnings no errors
            N = "N" # not imported
            U = "U" # translation updated need to reimport
    
    Args:
        db (TimelinkDatabase): timelink database
        kleio_files (List[KleioFile]): list of kleio files with extra field import_status
        match_path (bool, optional): if True, match the path of the kleio file with the path of the imported file. Defaults to False.

    Returns:
        List[KleioFile]: list of kleio files with field import_status
    """


    previous_imports: List[KleioImportedFile] = db.get_imported_files()
    if match_path:
        imported_files_dict = {imported.path:imported for imported in previous_imports}
        valid_files_dict = {file.path: file for file in kleio_files}
    else:
        imported_files_dict = {imported.name:imported for imported in previous_imports}
        valid_files_dict = {file.name: file for file in kleio_files}
    
    for path,file in valid_files_dict.items():
        if path not in imported_files_dict:
            file.import_status = import_status_enum.N
        elif file.translated > imported_files_dict[path].imported.replace(tzinfo=timezone.utc):
            file.import_status = import_status_enum.U
        else:
            if imported_files_dict[path].nerrors >  0:
                file.import_status = import_status_enum.E
            elif imported_files_dict[path].nwarnings > 0:
                file.import_status = import_status_enum.W
            else:
                file.import_status = import_status_enum.I
    return kleio_files