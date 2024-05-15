""" Database connection and setup

TODO:

- use logging to database functions.
- add mysql support


"""

from datetime import timezone
import os
import random
import string
import time
import re
import warnings
import logging

from typing import List
from pydantic import TypeAdapter

from sqlalchemy import Engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import select, func
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import create_database
import docker  # pylint: disable=import-error

import timelink
from timelink.kleio.kleio_server import is_docker_running
from timelink.mhk import utilities
from timelink.api import models  # pylint: disable=unused-import
from timelink.api.models import Entity, PomSomMapper
from timelink.api.models import pom_som_base_mappings
from timelink.api.models import Person
from timelink.api.models import Attribute
from timelink.api.models import KleioImportedFile
from timelink.api.models.system import KleioImportedFileSchema
from timelink.kleio import KleioServer, KleioFile, import_status_enum
from timelink.kleio.importer import import_from_xml
from . import views  # see https://github.com/sqlalchemy/sqlalchemy/wiki/Views

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
    postgres_containers: docker.models.container.Container = client.containers.list(
        filters={"ancestor": "postgres"}
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
        logging.debug(f"Waiting for postgres server to start: {elapsed_time} seconds")
        cont = client.containers.get(psql_container.id)
        elapsed_time += stop_time
    if cont.status != "running":
        raise RuntimeError("Postgres server did not start")

    while True:
        # Execute the 'pg_isready' command in the container
        exit_code, output = psql_container.exec_run("pg_isready")

        # If the 'pg_isready' command succeeded, break the loop
        if exit_code == 0:
            logging.info("Postgres server is ready")
            break

        # If the 'pg_isready' command failed, wait for 1 seconds and try again
        time.sleep(1)

    return psql_container


def random_password():
    """Generate a random password"""

    letters = string.ascii_letters
    result_str = "".join(random.choice(letters) for i in range(10))
    return result_str


def get_db_password():
    # get password from environment
    db_password = os.environ.get("TIMELINK_DB_PASSWORD")
    if db_password is None:
        db_password = random_password()
        os.environ["TIMELINK_DB_PASSWORD"] = db_password
    return db_password


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
    else:
        return []


def get_sqlite_databases(directory_path: str) -> list[str]:
    """Get the sqlite databases in a directory
    Args:
        directory_path (str): directory path
    Returns:
        list[str]: list of sqlite databases
    """
    cd = os.getcwd()
    sqlite_databases = []
    for root, _dirs, files in os.walk(directory_path):
        for file_name in files:
            if file_name.endswith(".sqlite"):
                db_path = os.path.join(root, file_name)
                # path relative to cd
                db_path = os.path.relpath(db_path, cd)
                sqlite_databases.append(db_path)
    return sqlite_databases


def is_valid_postgres_db_name(db_name):
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


class TimelinkDatabase:
    """Database connection and setup

    Creates a database connection and session. If the database does not exist,
    it is created. **db_type** determines the type of database.

    Currently, only sqlite and postgres are supported.

    * If db_type is sqlite, the database is created in the current directory.
    * If db_type is postgres or mysql, the database is created in a docker container.
    * If the database is postgres, the container is named timelink-postgres.
    * If the database is mysql, the container is named timelink-mysql.

    Attributes:
        db_url (str): database sqlalchemy url
        db_name (str): database name
        db_user (str): database user (only for postgres databases)
        db_pwd (str): database password (only for postgres databases)
        engine (Engine): database engine
        session (Session): database session factory
        metadata (MetaData): database metadata
        db_container: database container
        kserver: kleio server attached to this database, used for imports


    """

    db_url: str
    db_name: str
    db_user: str
    db_pwd: str
    db_type: str
    pattributes: Table | None = None
    eattributes: Table | None = None
    nfuncs: Table | None = None
    kserver: KleioServer | None = None

    def __init__(
        self,
        db_name: str = "timelink",
        db_type: str = "sqlite",
        db_url=None,
        db_user=None,
        db_pwd=None,
        db_path=None,
        kleio_server=None,
        kleio_home=None,
        kleio_image=None,
        kleio_version=None,
        kleio_token=None,
        kleio_update=None,
        postgres_image=None,
        postgres_version=None,
        stop_duplicates=True,
        **connect_args,
    ):
        """Initialize the database connection and setup

        Example:
            .. code-block:: python

                db = TimelinkDatabase('timelink', 'sqlite')
                with db.session() as session:
                    # do something with the session
                    session.commit()

        Args:
            db_name (str, optional): database name; defaults to "timelink".
            db_type (str, optional): database type; defaults to "sqlite".
            db_url (str, optional): database url. If None, a url is generated; defaults to None
            db_user (str, optional): database user; defaults to None.
            db_pwd (str, optional): database password; defaults to None.
            db_path (str, optional): database path (for sqlite databases); defaults to None.
            kleio_server (KleioServer, optional): kleio server for imports; defaults to None.
            kleio_home (str, optional): kleio home directory; defaults to None. If present and
                                        kleio_server is None will start new kleio server, which
                                        can be fetched with get_kleio_server()
            kleio_image (str, optional): kleio docker image. Passed to KleioServer().
            kleio_version (str, optional): kleio version. Passed to KleioServer().
            kleio_token (str, optional): kleio token. Passed to KleioServer().
            kleio_update (bool, optional): update kleio server. Passed to KleioServer().
            postgres_image (str, optional): postgres docker image; defaults to None.
            postgres_version (str, optional): postgres version; defaults to None.
            extra_args (dict, optional): extra arguments to sqlalchemy and
                                        :func:`timelink.kleio.KleioServer.start`
        """
        if db_name is None:
            db_name = "timelink"
        self.db_name = db_name

        # if we received a url, use it to connect
        if db_url is not None:
            self.db_url = db_url
        # if not, generate a url from other parameter
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
                    self.db_url = f"sqlite:///{db_path}/{self.db_name}.sqlite"
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
                    usr = [var for var in container_vars if "POSTGRES_USER" in var][0]
                    self.db_user = usr.split("=")[1]
                else:
                    self.db_container = start_postgres_server(
                        self.db_name,
                        self.db_user,
                        self.db_pwd,
                        image=postgres_image,
                        version=postgres_version,
                    )
                self.db_url = (
                    f"postgresql://{self.db_user}:"
                    f"{self.db_pwd}@localhost/{self.db_name}"
                )
                self.db_container = start_postgres_server(
                    self.db_name, self.db_user, self.db_pwd
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

        if kleio_server is not None:
            self.set_kleio_server(kleio_server)
        else:
            if kleio_home is not None:
                self.kserver: KleioServer = KleioServer.start(
                    kleio_home=kleio_home,
                    kleio_image=kleio_image,
                    kleio_version=kleio_version,
                    kleio_admin_token=kleio_token,
                    update=kleio_update,
                    stop_duplicates=stop_duplicates,
                )

    def set_kleio_server(self, kleio_server: KleioServer):
        """Set the kleio server for imports

        Args:
            kleio_server (KleioServer): kleio server
        """
        self.kserver = kleio_server

    def get_kleio_server(self):
        """Return the kleio server associated with this database"""
        return self.kserver

    def create_tables(self):
        """Creates the tables from the current ORM metadata if needed

        :return: None
        """
        self.metadata.create_all(self.engine)  # only creates if missing

    def create_views(self):
        """Creates the views


        :return: None
        """
        self.pattributes = self.get_pattribute_view()
        self.eattributes = self.get_eattribute_view()

    def table_names(self):
        """Current tables in the database"""
        insp = inspect(self.engine)
        db_tables = insp.get_table_names()  # tables in the database
        return db_tables

    def table_row_count(self) -> List[tuple[str, int]]:
        """Number of rows of each table in the database

        Returns:
            list: list of tuples (table_name, row_count)"""

        tables_names = self.table_names()

        row_count = []
        with self.session() as session:
            for table in tables_names:
                length = session.scalar(select(func.count()).select_from(text(table)))
                row_count.append((table, length))
        return row_count

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

    def get_imported_files(self) -> List[KleioImportedFileSchema]:
        """Returns the list of imported files in the database."""
        result = self.session().query(KleioImportedFile).all()
        # Convert to Pydantic Schema
        # https://stackoverflow.com/questions/55762673/how-to-parse-list-of-models-with-pydantic
        ta = TypeAdapter(List[KleioImportedFileSchema])
        result_pydantic = ta.validate_python(result)
        return result_pydantic

    def get_import_status(
        self, kleio_files: List[KleioFile] = None, status=None, match_path=False
    ) -> List[KleioFile]:
        """Get the import status of the kleio files

        See :func:`timelink.api.database.get_import_status`

        """
        if kleio_files is None:
            if self.get_kleio_server() is None:
                raise ValueError(
                    "Empty list of files. \n"
                    "Either provide list of files or attache database to Kleio server."
                )
            else:
                kleio_files = self.get_kleio_server().translation_status(
                    path="", recurse="yes"
                )
        files: List[KleioFile] = get_import_status(self, kleio_files, match_path)
        if status is not None:
            files = [file for file in files if file.import_status.value == status]
        return files

    def get_need_import(
        self,
        kleio_files: List[KleioFile],
        with_import_errors=False,
        with_import_warnings=False,
        match_path=False,
    ) -> List[KleioFile]:
        """Get the kleio files that need import

        These are the files that were never imported or that were updated
        after import (status N and U). Use include_errors and include_warnings set
        to true to also include files previously imported with errors and warnings.

        Args:
            kleio_files (List[KleioFile]): list of kleio files
            with_import_errors (bool, optional): if True, include files with errors;
                                                defaults to False.
            with_import_warnings (bool, optional): if True, include files with warnings;
                                            defaults to False.
            match_path (bool, optional): if True, match the path of the kleio file with
                                            the path of the imported file; defaults to False.

        Returns:
            List[KleioFile]: list of kleio files with field import_status
        """

        kleio_files: List[KleioFile] = get_import_status(self, kleio_files, match_path)
        return [
            file
            for file in kleio_files
            if (
                file.import_status == import_status_enum.N
                or file.import_status == import_status_enum.U  # noqa: W503
            )
            or (  # noqa: W503
                with_import_errors and file.import_status == import_status_enum.E
            )
            or (  # noqa: W503
                with_import_warnings and file.import_status == import_status_enum.W
            )  # noqa: W503
        ]

    def get_import_rpt(self, path: str, match_path=False) -> str:
        """Get the import report of a file in the database"""
        with self.session() as session:
            if match_path:
                result = (
                    session.query(KleioImportedFile)
                    .filter(KleioImportedFile.path == path)
                    .first()
                )
            else:
                result = (
                    session.query(KleioImportedFile)
                    .filter(KleioImportedFile.name == path)
                    .first()
                )
            if result is not None:
                s = result.error_rpt + "\n" + result.warning_rpt
            else:
                s = "No import report found"
        return s

    def update_from_sources(
        self,
        path=None,
        with_translation_warnings=True,
        with_translation_errors=False,
        with_import_errors=False,
        with_import_warnings=False,
        match_path=False,
    ):
        """Update the database from the sources.

        Needs an attached KleioServer.


        Args:
            path (str): path to the sources, if None all the sources are updated.
            with_translation_warnings (bool, optional): if True, import files with translation warnings;
                                            defaults to True.
            with_translation_errors (bool, optional): if True, import files with tr errors; defaults to False.
            with_import_errors (bool, optional): if True, re-import files with errors; defaults to False.
            with_import_warnings (bool, optional): if True, re-import files with warnings; defaults to False.
            match_path (bool, optional): if True, match the path of the kleio file with the
                                          path of the imported file; if False just match the
                                          file name; defaults to False.

        """
        logging.debug("Updating from sources")
        if self.kserver is None:
            raise ValueError("No kleio server attached to this database")
        else:
            if path is None:
                path = ""
                logging.debug("Path set to ''")
            for kfile in self.kserver.translation_status(
                path=path, recurse="yes", status="T"
            ):
                logging.info(
                    f"Request translation of {kfile.status.value} {kfile.path}"
                )
                self.kserver.translate(kfile.path, recurse="no", spawn="no")
            # wait for translation to finish
            logging.debug("Waiting for translations to finish")
            pfiles = self.kserver.translation_status(path="", recurse="yes", status="P")

            qfiles = self.kserver.translation_status(path="", recurse="yes", status="Q")
            # TODO: change to import as each translation finishes
            while len(pfiles) > 0 or len(qfiles) > 0:
                time.sleep(1)

                pfiles = self.kserver.translation_status(
                    path="", recurse="yes", status="P"
                )
                qfiles = self.kserver.translation_status(
                    path="", recurse="yes", status="Q"
                )
            # import the files
            to_import = self.kserver.translation_status(
                path="", recurse="yes", status="V"
            )
            if with_translation_warnings:
                to_import += self.kserver.translation_status(
                    path="", recurse="yes", status="W"
                )
            if with_translation_errors:
                to_import += self.kserver.translation_status(
                    path="", recurse="yes", status="E"
                )
            # https://github.com/time-link/timelink-py/issues/40
            import_needed = self.get_need_import(
                to_import,
                with_import_errors,
                with_import_warnings,
                match_path=match_path,
            )

            for kfile in import_needed:
                kfile: KleioFile
                with self.session() as session:
                    try:
                        logging.info(f"Importing {kfile.path}")
                        # TODO: #18 expose import_from_xml in TimelinkDatabase
                        stats = import_from_xml(
                            kfile.xml_url,
                            session=session,
                            options={
                                "return_stats": True,
                                "kleio_token": self.kserver.get_token(),
                                "kleio_url": self.kserver.get_url(),
                                "mode": "TL",
                            },
                        )
                        logging.debug(f"Imported {kfile.path}: {stats}")
                        time.sleep(1)
                    except Exception as e:
                        logging.error("Unexpected error:")
                        logging.error(f"Error: {e}")
                        continue

    def query(self, query_spec):
        """Executes a query in the database

        Args:
            query: sqlAlchemy query"""

        with self.session() as session:
            result = session.query(query_spec)
        return result

    def get_person(self, id: str = None, sql_echo: bool = False) -> Person:
        """Fetch a person by id.

        Args:
            id (str, optional): person id; defaults to None.
        """
        return timelink.api.models.person.get_person(id=id, db=self, sql_echo=sql_echo)

    def get_entity(self, id: str = None) -> Entity:
        """Fetch an entity by id.

        Args:
            id (str, optional): entity id; defaults to None.
        """
        with self.session() as session:
            result = Entity.get_entity(id=id, session=session)
        return result

    def pperson(self, id: str):
        """Prints a person in kleio notation"""
        print(self.get_person(id=id).to_kleio())

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

    def get_table(self, class_id: str):
        """Get the ORM table for a entity type

        Returns:
            Table
        """
        model = self.get_model(class_id)
        return model.__table__

    def get_pattribute_view(self):
        """Return the nattribute view.

        Returns a sqlalchemy table linked to the pattributes view of timelink/MHK databases
        This views joins the table "persons" and the table "attributes" providing attribute
        values with person names and sex.

        The column id contains the id of the person/object, not of the attribute

        Returns:
            A table object with the pattribute view

        Original SQL code

        .. code-block:: sql

            CREATE VIEW pattributes AS
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
        if self.pattributes is None:
            eng: Engine = self.engine
            metadata: MetaData = self.metadata
            # texists = inspect(eng).has_table("pattributes")

            person = Person.__table__
            attribute = Attribute.__table__
            attr = views.view(
                "nattributes",
                metadata,
                select(
                    person.c.id.label("id"),
                    person.c.name.label("name"),
                    person.c.sex.label("sex"),
                    attribute.c.the_type.label("the_type"),
                    attribute.c.the_value.label("the_value"),
                    attribute.c.the_date.label("the_date"),
                    person.c.obs.label("pobs"),
                    attribute.c.obs.label("aobs"),
                ).select_from(
                    person.join(attribute, person.c.id == attribute.c.entity)
                ),
            )
            self.pattributes = attr
            with eng.begin() as con:
                metadata.create_all(con)
        return self.pattributes

    def get_eattribute_view(self):
        """Return the eattribute view.

        Returns a sqlalchemy table with a view that joins the table "entities"
        and the table "attributes". This view provides attribute values with
        the "positional" information kept in the entities tables, such as
        line number, level and order in the source file as well as groupname of
        the attribute ("ls", "attr", etc...) and timestamps for updates and indexing.
        """
        if self.eattributes is None:
            eng: Engine = self.engine
            metadata: MetaData = self.metadata
            # texists = inspect(eng).has_table("eattributes")

            entity = Entity.__table__
            attribute = Attribute.__table__
            attr = views.view(
                "eattributes",
                metadata,
                select(
                    entity.c.id.label("id"),
                    entity.c.the_line.label("the_line"),
                    entity.c.the_level.label("the_level"),
                    entity.c.the_order.label("the_order"),
                    entity.c.groupname.label("groupname"),
                    entity.c.updated.label("updated"),
                    entity.c.indexed.label("indexed"),
                    attribute.c.entity.label("entity"),
                    attribute.c.the_type.label("the_type"),
                    attribute.c.the_value.label("the_value"),
                    attribute.c.the_date.label("the_date"),
                    attribute.c.obs.label("aobs"),
                ).select_from(entity.join(attribute, entity.c.id == attribute.c.id)),
            )
            self.eattributes = attr
            with eng.begin() as con:
                metadata.create_all(con)
        return self.eattributes

    def export_as_kleio(
        self,
        ids: List,
        filename,
        kleio_group: str = None,
        source_group: str = None,
        act_group: str = None,
    ):
        """Export entities to a kleio file

        Renders each of the entities in the list in kleio format
        using Entity.to_kleio() and writes them to a file.

        If provded, kleio_group, source_group and act_group are written
        before the entities.


        Args:
            ids (List): list of ids
            filename ([type]): destination file path
            kleio_group ([type]): text to be used as initial kleio group
            source_group ([type]): text to be used as source group
            act_group ([type]): text to be used as act group
        """

        with open(filename, "w") as f:
            if kleio_group is not None:
                f.write(f"{kleio_group}\n")
            if source_group is not None:
                f.write(f"{source_group}\n")
            if act_group is not None:
                f.write(f"{act_group}\n")
            for id in ids:
                with self.session() as session:
                    ent = Entity.get_entity(id, session)
                    f.write(str(ent.to_kleio()) + "\n\n")


def get_import_status(
    db: TimelinkDatabase, kleio_files: List[KleioFile], match_path=False
) -> List[KleioImportedFileSchema]:
    """Get the import status of the kleio files.

        The status in returned
        in :attr:`timelink.api.models.system.KleioImportedFileSchema.import_status`

    Args:
        db (TimelinkDatabase): timelink database
        kleio_files (List[KleioFile]): list of kleio files with extra field import_status
        match_path (bool, optional): if True, match the path of the kleio file
                                    with the path of the imported file;
                                    defaults to False.

    Returns:
        List[KleioImportedFileSchema]: list of kleio files with field import_status

    TODO: KleioFile should also receive the import_errors and import_warnings
    """

    previous_imports: List[KleioImportedFileSchema] = db.get_imported_files()
    if match_path:
        imported_files_dict = {imported.path: imported for imported in previous_imports}
        valid_files_dict = {file.path: file for file in kleio_files}
    else:
        imported_files_dict = {imported.name: imported for imported in previous_imports}
        valid_files_dict = {file.name: file for file in kleio_files}
        if len(valid_files_dict) != len(kleio_files):
            raise ValueError(
                "Some kleio files have the same name. "
                "Use match_path=True to match the full path of the kleio file "
                "with the path of the imported file."
            )

    for path, file in valid_files_dict.items():
        if path not in imported_files_dict or file.translated is None:
            file.import_status = import_status_enum.N
        elif file.translated > imported_files_dict[path].imported.replace(
            tzinfo=timezone.utc
        ):
            file.import_status = import_status_enum.U
        else:
            file.import_errors = imported_files_dict[path].nerrors
            file.import_warnings = imported_files_dict[path].nwarnings
            file.import_error_rpt = imported_files_dict[path].error_rpt
            file.import_warning_rpt = imported_files_dict[path].warning_rpt
            file.imported = imported_files_dict[path].imported
            file.imported_string = imported_files_dict[path].imported_string
            if imported_files_dict[path].nerrors > 0:
                file.import_status = import_status_enum.E
            elif imported_files_dict[path].nwarnings > 0:
                file.import_status = import_status_enum.W
            else:
                file.import_status = import_status_enum.I
    return kleio_files
