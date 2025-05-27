"""Database connection and setup

TODO:

- use logging to database functions.
- add mysql support


"""

# pylint: disable=unused-import
from collections import defaultdict, namedtuple
import os
import time
import warnings
import logging

# import pdb

from typing import List
from pydantic import TypeAdapter, BaseModel
import pandas as pd

from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import select, func, union
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy.orm import aliased
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import create_database, drop_database
from sqlalchemy.sql.selectable import TableClause

import timelink
from timelink import migrations
from timelink.api.models.act import Act
from timelink.api.models.geoentity import Geoentity
from timelink.api.models.object import Object
from timelink.mhk import utilities
from timelink import models  # pylint: disable=unused-import
from timelink.api.models.base_class import Base, get_all_base_subclasses
from timelink.api.models import Entity, PomSomMapper
from timelink.api.models import pom_som_base_mappings
from timelink.api.models import Person
from timelink.api.models import Attribute
from timelink.api.models import KleioImportedFile
from timelink.api.models.system import KleioImportedFileSchema
from timelink.kleio import KleioServer, KleioFile, import_status_enum
from timelink.kleio.importer import import_from_xml
from timelink.mhk.models.relation import Relation

from . import views  # see https://github.com/sqlalchemy/sqlalchemy/wiki/Views

from .database_utils import get_db_password, get_import_status, random_password
from .database_postgres import get_postgres_container_pwd, is_postgres_running
from .database_postgres import start_postgres_server, get_postgres_container
from .database_postgres import get_postgres_url  # noqaO
from .database_postgres import get_postgres_dbnames  # noqa
from .database_postgres import get_postgres_container_user  # noqa
from .database_postgres import is_valid_postgres_db_name  # noqa
from .database_sqlite import get_sqlite_databases, get_sqlite_url  # noqa


class TimelinkDatabaseSchema(BaseModel):
    """Pydantic schema for TimelinkDatabase"""

    db_name: str
    db_type: str


class TimelinkDatabase:
    """Database connection and setup"""

    db_url: str
    db_name: str
    db_user: str
    db_pwd: str
    db_type: str
    kserver: KleioServer | None = None

    def __init__(
        self,
        db_name: str = "timelink",
        db_type: str = "sqlite",
        db_url=None,
        db_user=None,
        db_pwd=None,
        db_path=None,
        drop_if_exists=False,
        kleio_server=None,
        kleio_home=None,
        kleio_image=None,
        kleio_version=None,
        kleio_token=None,
        kleio_update=None,
        postgres_image=None,
        postgres_version=None,
        stop_duplicates=True,
        echo=False,
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
            drop_if_exists (bool, optional): if True, drop the database if it exists; defaults to False.
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
            echo (bool, optional): if True, the Engine will log all statements; defaults to False.
            connect_args (dict, optional): extra arguments to sqlalchemy and
                           :func:`timelink.kleio.KleioServer.start`
        """
        if db_name is None:
            db_name = "timelink"
        self.db_name = db_name
        self.db_type = db_type

        self.views = dict()
        self.kserver = None
        self.base_tables_names = []

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
                    pwd = [var for var in container_vars if "POSTGRES_PASSWORD" in var][0]
                    pwd_value = pwd.split("=")[1]
                    self.db_pwd = pwd_value
                    usr = [var for var in container_vars if "POSTGRES_USER" in var][0]
                    usr_value = usr.split("=")[1]
                    self.db_user = usr_value
                else:
                    self.db_container = start_postgres_server(
                        self.db_name,
                        self.db_user,
                        self.db_pwd,
                        image=postgres_image,
                        version=postgres_version,
                    )
                self.db_url = f"postgresql://{self.db_user}:" f"{self.db_pwd}@localhost/{self.db_name}"
                self.db_container = start_postgres_server(self.db_name, self.db_user, self.db_pwd)
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

        self.engine = create_engine(self.db_url, echo=echo, connect_args=connect_args)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        self.metadata = Base.metadata
        self.registry = Base.registry

        # remove dynamic tables
        # wee need this to avoid problems of persistence of dynamic tables
        # and dynamic ORM from one database to another.
        #

        # create an empty database if it does not exist
        if drop_if_exists:
            if database_exists(self.engine.url):
                drop_database(self.engine.url)
        if not database_exists(self.engine.url) or db_url == "sqlite:///:memory:":  # noqa
            try:
                create_database(self.engine.url)  # create empty database
                self.create_db()  # creates the tables and views selectively
            except Exception as exc:
                logging.error(exc)
                raise Exception("Error while creating database") from exc
        else:
            try:

                self.check_db()  # health check to the database
                migrations.upgrade(self.db_url)
                with self.session() as session:
                    self._ensure_all_mappings(session)  # this will cache the pomsom mapper objects
                # ensure views
                self._update_views()
                # get any extra table or views inspecting metadata
                self.metadata.reflect(bind=self.engine)

            except Exception as exc:
                logging.error(exc)
                raise exc

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

    def create_db(self):
        """Create the database

        Will create the tables and views if they do not exist
        Will load the database classes and ensure all mappings
        Will stamp the database with alembic as most recent version
        """

        # pdb.set_trace()
        # Clean caches of Mappings and ORM classes
        PomSomMapper.reset_cache()
        Entity.reset_cache()

        # remove dynamic tables from metadata
        for dtable in self.db_dynamic_tables():
            self.metadata.remove(dtable)

        self._create_tables()

        try:
            migrations.stamp(self.db_url, "head")
        except Exception as exc:
            logging.error(exc)

        with self.session() as session:
            try:
                session.commit()
                session.rollback()
                session.expire_on_commit = False
                self._load_database_classes(session)
                self._ensure_all_mappings(session)
                session.commit()
            except Exception as exc:
                logging.error(f"Error during database initialization: {exc}")
                session.rollback()
        try:
            self._update_views()
        except Exception as exc:
            logging.error(exc)
            raise Exception("Error while updating database views") from exc

    def check_db(self):
        """Check the database health"""
        db_tables = self.db_table_names()
        orm_tables = Entity.get_orm_table_names()
        missing = set(orm_tables) - set(db_tables)
        if len(missing) > 0:
            logging.warning(f"Missing tables in database: {missing}")
            logging.warning("Creating tables")
            # we need to create the tables
            # remove dynamic tables from metadata
            for dtable in self.db_dynamic_tables():
                self.metadata.remove(dtable)
            try:
                self.metadata.create_all(self.engine)  # create the tables
                migrations.stamp(self.db_url, "head")
            except Exception as exc:
                logging.error(f"Error creating tables: {exc}")
        else:
            logging.info("Database is healthy")

        # check if database is postgres and has the link_status type defined
        if self.db_type == "postgres":
            with self.engine.connect() as connection:
                result = connection.execute(
                    select(text("1")).where(text("EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linkstatus')"))
                )
                if result.scalar() is not None:
                    logging.warning("link_status found, deleting it")
                    result = connection.execute(text("DROP TYPE IF EXISTS link_status CASCADE"))
                    # result = connection.execute(
                    #     text("CREATE TYPE link_status AS ENUM ('valid', 'invalid', 'possible')")
                    # )

    def _build_dependency_graph(self, tables):
        """Builds a dependency graph of tables based on foreign key constraints.

        co-pilot generated this code
        """
        graph = defaultdict(set)
        for table in tables:
            for fk in table.foreign_keys:
                graph[table.name].add(fk.column.table.name)
        return graph

    def _topological_sort(self, graph):
        """Performs topological sort on the dependency graph.

        Topological sort is an algorithm for ordering the nodes
        in a directed acyclic graph (DAG) such that for every
        directed edge from node A to node B, node A appears
        before node B in the ordering. In our case, the
        nodes are tables, and the directed edges represent
        foreign key dependencies.

        Here's an implementation of topological sort using Kahn's algorithm:

        co-pilot generated this code
        """
        in_degree = defaultdict(int)  # Count incoming edges for each node
        for table, dependencies in graph.items():
            for dependency in dependencies:
                if dependency != table:
                    in_degree[table] += 1

        queue = [table for table in graph if in_degree[table] == 0]  # Start with nodes with no incoming edges
        sorted_tables = []

        while queue:
            table = queue.pop(0)
            sorted_tables.append(table)

            for dependent in list(graph.keys()):
                if table in graph[dependent]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        if sum(in_degree.values()) > 0:
            raise ValueError("Circular dependency detected in the database schema.")

        return sorted_tables

    def _create_tables(self):
        """Creates the tables from the current ORM metadata if needed

        This method is normally called after an empty database is created
        to populate the database with the basic table associated with the
        builtin ORM Models (that inherit from timelink.api.models.Base).

        :return: None
        """
        try:
            self.metadata.create_all(self.engine)
        except Exception as exc:
            logging.error(f"Error creating tables: {exc}")
            raise exc

    def _drop_views(self):
        """Drop views"""

        existing = self.view_names()
        with self.session() as session:
            try:
                for view_name in existing:
                    stmt = views.DropView(view_name).execute_if(callable_=views.view_exists)
                    session.execute(stmt)
                    session.commit()
            except Exception as exc:
                session.rollback()
                logging.error(f"Error dropping view {view_name}: {exc}")

    def _create_views(self):
        """Creates the views

        eattributes: view of the entity attributes linked with entity information
        pattributes: view of the person attributes linked with person information
        named_entities: view of the named entities linked with entity information
        nfunctions: view of the functions of people in acts linked with entity information
        See issue #63
        :return: None
        """
        view = self._create_nattributes_view()
        self.views[view.name] = view
        view = self._create_eattribute_view()
        self.views[view.name] = view
        view = self._create_named_entity_view()
        self.views[view.name] = view
        view = self._create_nfunction_view()
        self.views[view.name] = view
        view = self._create_nrelations_view()
        self.views[view.name] = view

        try:
            self.metadata.create_all(self.engine)

        except Exception as exc:
            logging.error(f"Error creating views: {exc}")

    def _update_views(self):
        """Drop and recreate all views"""
        self._drop_views()
        self._create_views()

    def drop_db(self, session=None, timelink_only=False):
        """
        This will drop the database.

        If only timelink related tables are to be dropped, set timelink_only=True.

        If timelink_only=True (default is False) will not touch non timelink tables that might exist.

        Args:
            timelink_only (bool, optional): If True, only drop timelink related tables; defaults to False.
            session (Session, optional): Database session to use; defaults to None.

        """

        if not timelink_only:
            if ":memory:" not in self.db_url:
                drop_database(self.db_url)
            return

        if session is None:
            session = self.session()

        try:
            session.rollback()
            self._load_database_classes(session)
            self._ensure_all_mappings(session)
            session.commit()
            session.close()

            self.metadata = models.Base.metadata
        except Exception as exc:
            logging.error(f"Error during database drop: {exc}")
            session.rollback()
        try:
            with self.engine.begin() as con:
                dynamic_tables = self.db_dynamic_tables()
                # first the dynamic tables
                self.metadata.drop_all(con, tables=dynamic_tables)
                # then the rest
                self.metadata.drop_all(con)
        except Exception as exc:
            warnings.warn("Dropping tables problem " + str(exc), stacklevel=2)

    #
    # Interaction with Kleio Server
    #
    def set_kleio_server(self, kleio_server: KleioServer):
        """Set the kleio server for imports

        Args:
            kleio_server (KleioServer): kleio server
        """
        self.kserver = kleio_server

    def get_kleio_server(self):
        """Return the kleio server associated with this database"""
        return self.kserver

    #
    # Introspect Timelink database
    #
    def get_database_version(self):
        """Get the alembic version string for this db"""
        with self.engine.connect() as connection:
            result = connection.execute(select(text("version_num")).select_from(text("alembic_version")))
            version = result.scalar()
        return version

    def db_table_names(self):
        """Current tables in the database"""
        insp = inspect(self.engine)
        db_tables = insp.get_table_names()  # tables in the database
        return db_tables

    def db_orm_tables(self):
        """Orm tables in the database

        These are the tables managed by SQLAlchemy ORM.
        These tables should be present in the database.

        These include:
        * All the tables of the timelink data model (Entity and its subclasses)
        * Other auxiliary tables managed with SQLAlchemy ORM like class_attributes
          and Kleio imported files, syspar, syslog, etc.
        * Dynamically created tables during import (see db_dynamic_tables)

        Returns:
            list: list of table objects
        """
        all_subclasses = get_all_base_subclasses()
        return [ormclass.__mapper__.local_table for ormclass in all_subclasses]

    def db_base_table_names(self):
        """Names of base tables in the database
        These are the tables included in the base mappings,
        i.e., the tables that are not dynamically created
        plus the classes table
        """
        r = [pom_som_base_mappings[k][0].table_name for k in pom_som_base_mappings.keys()]
        return list(set(r + ["classes"]))

    def db_base_tables(self):
        """Base tables in the database

        These are the tables included in the base mappings,
        i.e., the tables that are not dynamically created
        """
        return [self.metadata.tables[table_name] for table_name in self.db_base_table_names()]

    def db_dynamic_tables(self):
        """Dynamic tables in the database.

        These are the tables created dynamically when importing data,
        with orm classes also dymamically created.

        """
        entity_based_tables = [
            ormclass.__mapper__.local_table for ormclass in Entity.get_subclasses() if ormclass.is_dynamic()
        ]
        return list(set(entity_based_tables) - set(self.db_base_tables()))

    def orm_table_names(self):
        """Current tables associated with ORM models"""
        return Entity.get_orm_table_names()

    def view_names(self):
        """Get the list of views in the database"""
        inspector = inspect(self.engine)
        return inspector.get_view_names()

    def get_view(self, view_name: str):
        """Get a view by name"""
        return self.views[view_name]

    def get_view_columns(self, view_name: str):
        """Get the columns of a view"""
        view = self.get_view(view_name)
        return list(view.columns)

    def table_row_count(self) -> List[tuple[str, int]]:
        """Number of rows of each table in the database

        Returns:
            list: list of tuples (table_name, row_count)"""

        tables_names = self.db_table_names()

        row_count = []
        with self.session() as session:
            for table in tables_names:
                length = session.scalar(
                    select(func.count()).select_from(  # pylint: disable=not-callable
                        text(table)
                    )  # pylint: disable=not-callable
                )  # pylint: disable=not-callable
                row_count.append((table, length))
        return row_count

    #
    # Mapping
    def _load_database_classes(self, session):
        """
        Populates database with core Database classes
        :param session:
        :return:
        """

        # Check if the core tables are there
        existing_tables = self.db_table_names()

        missing = set(self.db_base_table_names()) - set(existing_tables)
        # If any of the core tables are missing, create all tables based on ORM metadata
        # NOTE: tables are not created based on the pom_som_base_mappings definitions
        # because the ORM metadata is the source of truth

        if len(missing) > 0:
            self._create_tables()  # ORM metadata trumps pom_som_base_mappings

        # check if we have the data for the core database entity classes
        stmt = select(PomSomMapper.id)
        available_mappings = session.execute(stmt).scalars().all()
        for k in pom_som_base_mappings.keys():  # pylint: disable=consider-iterating-dictionary
            if k not in available_mappings:
                data = pom_som_base_mappings[k]
                session.bulk_save_objects(data)
        # this will cache the pomsom mapper objects
        session.commit()

    def _ensure_all_mappings(self, session):
        """Ensure that all database classes have a table and ORM class"""

        pom_classes = PomSomMapper.get_pom_classes(session)
        for pom_class in pom_classes:
            if pom_class.table_name not in self.db_base_table_names():
                # this is dynamic pom_class
                pom_class.set_as_dynamic_pom()
            pom_class.ensure_mapping(session)

        # remove dynamic tables from metadata
        # at this point any table in the metadata that is not in
        # the database should be removed
        # this is necessary because the metadata is shared
        # between different databases
        # and the dynamic tables are not shared
        db_tables = self.db_table_names()
        for dtable in self.db_dynamic_tables():
            if dtable.name not in db_tables:
                self.metadata.remove(dtable)

        # Keep a dictionary of group names to ORM classes
        # this is necessary because the Kleio export file
        # only exports a class once, but a given source can
        # have multiple groups associated with the same class.
        # That is the case with persons, for example.
        # If later we want to know which ORM class to use for
        # for a given group, we can use this dictionary.
        # which is based on the actual class associated with each
        # group in the database.
        # This is also done during import but is needed here to
        # ensure that the ORM classes are available for queries

        # Clear cache of group to ORM mapping
        # this is necessary because the cache is kept in the
        # Entity class which can be used in different databases
        # in one programme.
        Entity.clear_group_models_cache()

        # now introspect the database for group/class combinations
        stmt = select(Entity.pom_class, Entity.groupname).distinct()
        results = session.execute(stmt).all()
        for pom_class, groupname in results:
            if groupname is not None:
                gname = groupname
            else:
                gname = "class"

            Entity.set_orm_for_group(gname, Entity.get_orm_for_pom_class(pom_class))

    #
    # Session utilities
    #
    def __enter__(self):
        return self.session()

    def __repr__(self):
        return f"TimelinkDatabase(db_type={self.db_type}, db_name={self.db_name})"

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

    #
    # Engine
    #
    def get_engine(self):
        """Get the database engine
        Returns:
            Engine: database engine
        """
        return self.engine

    #
    # Metadata
    #
    def get_metadata(self):
        """Get the database metadata
        Returns:
            MetaData: database metadata
        """
        return self.metadata

    #
    # Import files
    #
    def get_imported_files(self) -> List[KleioImportedFileSchema]:
        """Returns the list of imported files in the database."""
        result = self.session().query(KleioImportedFile).all()
        # Convert to Pydantic Schema
        # https://stackoverflow.com/questions/55762673/how-to-parse-list-of-models-with-pydantic
        ta = TypeAdapter(List[KleioImportedFileSchema])
        result_pydantic = ta.validate_python(result)
        return result_pydantic

    def get_import_status(
        self,
        kleio_files: List[KleioFile] = None,
        path=None,
        recurse=True,
        status=None,
        match_path=False,
    ) -> List[KleioFile]:
        """Get the import status of the kleio files

        The import status is stored in the database.
        This method retrieves the import status of the kleio files.

        Args:
            kleio_files (List[KleioFile], optional): list of kleio files; defaults to None.
            path (str, optional): path to the sources; defaults to None.
            recurse (bool, optional): if True, recurse the path; defaults to True.
            status (import_status_enum, optional): import status; defaults to None.
            math_path (bool, optional): if True, match the path of the kleio file with
                                        the path of the imported file; defaults to False
                                        (match just the file name).


        See :func:`timelink.api.database.get_import_status`

        """
        if kleio_files is None:
            if self.get_kleio_server() is None:
                raise ValueError(
                    "Empty list of files. \n" "Either provide list of files or attach database to Kleio server."
                )
            else:
                kleio_files = self.get_kleio_server().get_translations(path=path, recurse=recurse)
        if isinstance(kleio_files, KleioFile):
            kleio_files = [kleio_files]
        if not isinstance(kleio_files, list) or not all(isinstance(file, KleioFile) for file in kleio_files):
            raise ValueError(
                f"kleio_files must be a list of KleioFile objects."
                f"Use path={kleio_files} to get a list of KleioFile objects from a Kleio server."
            )

        files: List[KleioFile] = get_import_status(self, kleio_files=kleio_files, match_path=match_path)
        if status is not None:
            files = [file for file in files if file.import_status.value == status]
        return files

    def get_need_import(  # TODO: better name check_need_import
        self,
        kleio_files: List[KleioFile] = None,
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

        kleio_files: List[KleioFile] = self.get_import_status(kleio_files, match_path=match_path)
        return [
            file
            for file in kleio_files
            if (file.import_status == import_status_enum.N or file.import_status == import_status_enum.U)  # noqa: W503
            or (with_import_errors and file.import_status == import_status_enum.E)  # noqa: W503
            or (with_import_warnings and file.import_status == import_status_enum.W)  # noqa: W503  # noqa: W503
        ]

    def get_import_rpt(self, path: str, match_path=False) -> str:
        """Get the import report of a file in the database"""
        with self.session() as session:
            if match_path:
                result = session.query(KleioImportedFile).filter(KleioImportedFile.path == path).first()
            else:
                result = session.query(KleioImportedFile).filter(KleioImportedFile.name == path).first()
            if result is not None:
                s = result.error_rpt + "\n" + result.warning_rpt
            else:
                s = "No import report found"
        return s

    def update_from_sources(
        self,
        path=None,
        recurse=True,
        with_translation_warnings=True,
        with_translation_errors=False,
        with_import_errors=False,
        with_import_warnings=False,
        force=False,
        match_path=False,
    ):
        """Update the database from the sources.

        Needs an attached KleioServer.

        Args:
            path (str): path to the sources, if None all the sources are updated.
            recurse (bool, optional): if True, recurse the path; defaults to True.
            with_translation_warnings (bool, optional): if True, import files with translation warnings;
                                            defaults to True.
            with_translation_errors (bool, optional): if True, import files with tr errors; defaults to False.
            with_import_errors (bool, optional): if True, re-import files with errors; defaults to False.
            with_import_warnings (bool, optional): if True, re-import files with warnings; defaults to False.
            match_path (bool, optional): if True, match the path of the kleio file with the
                                          path of the imported file; if False just match the
                                          file name; defaults to False.
            force (bool): force the translation and subsequent import of valid files
        """
        logging.debug("Updating from sources")
        if self.kserver is None:
            raise ValueError("No kleio server attached to this database")
        else:
            if path is None:
                path = ""
                logging.debug("Path set to ''")

            if force:
                translate_status = None  # this gets all files, no matter status
            else:
                translate_status = "T"  # only those that need translation

            for kfile in self.kserver.get_translations(path=path, recurse=recurse, status=translate_status):
                logging.info("Request translation of %s %s", kfile.status.value, kfile.path)
                self.kserver.translate(kfile.path, recurse="no", spawn="no")
            # wait for translation to finish
            logging.debug("Waiting for translations to finish")
            pfiles = self.kserver.get_translations(path=path, recurse="yes", status="P")

            qfiles = self.kserver.get_translations(path=path, recurse="yes", status="Q")
            # TODO: change to import as each translation finishes
            while len(pfiles) > 0 or len(qfiles) > 0:
                time.sleep(1)

                pfiles = self.kserver.get_translations(path="", recurse="yes", status="P")
                qfiles = self.kserver.get_translations(path="", recurse="yes", status="Q")
            # import the files
            to_import = self.kserver.get_translations(path=path, recurse=recurse, status="V")  # TODO recurse make param
            if with_translation_warnings:
                to_import += self.kserver.get_translations(path=path, recurse=recurse, status="W")
            if with_translation_errors:
                to_import += self.kserver.get_translations(path=path, recurse=recurse, status="E")

            if force:
                import_needed = to_import
            else:
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
                        logging.info("Importing %s", kfile.path)
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
                        logging.debug("Imported %s: %s", kfile.path, stats)
                        time.sleep(1)
                    except Exception as e:
                        session.rollback()
                        logging.error("Unexpected error:")
                        logging.error("Error: %s", e)
                        continue

    def import_from_xml(self, file: str | KleioFile, kserver=None, return_stats=True):
        """Import one file

        Args:
           file (str | KleioFile): path to xml file or KleioFile object
            kserver (KleioServer, optional): Kleio server to use for import. Defaults to None.
            return_stats (bool, optional): Return import stats. Defaults to True.
        """
        if isinstance(file, KleioFile):
            path = file.xml_url
        else:
            path = file

        if kserver is None:
            kserver = self.kserver
        if kserver is None:
            raise ValueError("No kleio server attached to this database." "Attach kleio server or provide one in call.")
        # TODO: #18 expose import_from_xml in TimelinkDatabase
        stats = None
        with self.session() as session:
            try:
                stats = import_from_xml(
                    path,
                    session=session,
                    options={
                        "return_stats": return_stats,
                        "kleio_token": kserver.get_token(),
                        "kleio_url": kserver.get_url(),
                        "mode": "TL",
                    },
                )
            except Exception as e:
                session.rollback()
                logging.error(f"Error importing XML: {e}")
        return stats

    #
    # Timelink metadata inspection
    #
    def get_models_ids(self):
        """Get the ORM model classes as a list of ids

        Returns:
            list: list of ORM classes as string ids
        """
        return Entity.get_som_mapper_ids()

    def get_model(self, class_id: str | List[str], make_alias=None):
        """Get the ORM class for a entity type

        Args:
            class_id (str | List[str]): class id or list of class ids
            make_alias (bool, optional): if True, return an aliased ORM class;
                                         defaults to True in lists; False if single class_id.
        Returns:
            ORM class
        """
        if isinstance(class_id, list):
            if make_alias is None:
                make_alias = True
                return [self.get_model_by_name(c, make_alias=make_alias) for c in class_id]
        else:
            make_alias = False
            return self.get_model_by_name(class_id, make_alias=False)

    def get_model_by_name(self, class_or_groupname: str, make_alias=False):
        """Get the ORM class for a entity type by name
        or for a group name. If the name is not found, return None

        Args:
            class_or_groupname (str): class or group name

        Returns:
            ORM class aliased to avoid  # https://docs.sqlalchemy.org/en/20/errors.html#error-xaj2

        """

        orm_model = Entity.get_orm_for_pom_class(class_or_groupname)
        if orm_model is not None:
            if make_alias:
                return aliased(orm_model, flat=True)
            else:
                return orm_model
        else:
            orm_model = Entity.get_orm_for_group(class_or_groupname)
            if orm_model is None:
                return None
            if make_alias:
                return aliased(orm_model, flat=True)
            else:
                return orm_model

    def table_exists(self, table_name: str) -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name)

    def get_table(self, table_or_class: str | Entity) -> Table:
        """Get a table object from the database

        Args:
            table_or_class (str | Entity): table name, model name of ORM model

        Returns:
            sqlAlchemy Table: table object


        """
        if type(table_or_class) is str:
            if table_or_class in self.orm_table_names():
                model = Entity.get_tables_to_orm_as_dict()[table_or_class]
                if model is not None:
                    return model.__table__
            elif table_or_class in self.db_table_names():
                table = self.metadata.tables.get(table_or_class, None)
                if table is not None:
                    return table
                else:
                    table = Table(table_or_class, self.metadata, autoload_with=self.engine)
                    return table_or_class
            elif table_or_class in self.get_models_ids():
                model = self.get_model_by_name(table_or_class)
                if model is not None:
                    return model.__table__
        elif issubclass(table_or_class, Entity):
            return table_or_class.__table__
        return None

    def get_columns(self, class_or_table: str):
        """Get the columns for a entity type

        Returns:
            list: list of columns
        """

        Model = self.get_model_by_name(class_or_table, make_alias=False)
        if Model is None:
            if class_or_table in Entity.get_orm_table_names():
                return list(self.get_table(class_or_table).columns)
            elif class_or_table in self.view_names():
                return self.get_view_columns(class_or_table)
            else:
                raise ValueError(f"{class_or_table} not found")

        insp = inspect(Model)
        return list(insp.columns)

    def describe(self, argument, show=None, **kwargs):
        """Describe a table, view or a model
          if argument is a string, it is assumed to be a table or view
          if argument is a model, it is assumed to be a ORM model
          otherwise it is checked if it is a table object
          the method prints the columns of the table or model

        Args:
            argument: table name or model
            kwargs: additional arguments to pass to the describe method
            show: print the columns

        Returns:
            list: list of columns
        """
        columns = []
        argument_type = None
        if argument is None:
            argument_type = ""
            argument = "all kleio groups in the database"
            GroupModel = namedtuple("GroupModel", ["group", "table", "model"])
            return [GroupModel(group, orm.__tablename__, orm.__name__) for (group, orm) in Entity.group_models.items()]
        if isinstance(argument, str):
            if argument in self.get_models_ids():
                argument_type = "model"
                columns = self.get_columns(argument)
            elif self.get_model_by_name(argument) is not None:
                argument_type = "model"
                columns = self.get_columns(argument)
            elif argument in self.orm_table_names():
                argument_type = "model_table"
                Model = Entity.get_tables_to_orm_as_dict()[argument]
                insp = inspect(Model)
                columns = list(insp.columns)
            elif argument in self.db_table_names():
                argument_type = "non_model_table"
                insp = inspect.get_table(argument)
                columns = list(insp.columns)
        elif isinstance(argument, type) and issubclass(argument, Base):
            argument_type = "model"
            Model = argument
            insp = inspect(Model)
            columns = list(insp.columns)
        elif issubclass(type(argument), TableClause):
            argument_type = "table_like"
            columns = list(argument.columns)

        if len(columns) > 0 and show is not None:
            print(f"{str(argument)} ({argument_type})")
            for col in columns:
                fkey = str(col.foreign_keys) if col.foreign_keys else ""
                print(f"{col.name:<20} {str(col.table):<20} {str(col.type):<10} {fkey}")
        return columns

    #
    # Views
    #
    def _create_nattributes_view(self):
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
                attribute.c.id.label("attr_id"),
                attribute.c.the_type.label("the_type"),
                attribute.c.the_value.label("the_value"),
                attribute.c.the_date.label("the_date"),
                person.c.obs.label("pobs"),
                attribute.c.obs.label("aobs"),
            ).select_from(person.join(attribute, person.c.id == attribute.c.entity)),
        )
        # with eng.begin() as con:
        #     try:
        #         metadata.create_all(con)
        #     except Exception as exc:
        #         logging.error(f"Error creating view: {exc}")
        return attr

    def _create_eattribute_view(self):
        """Return the eattribute view.

        Returns a sqlalchemy table with a view that joins the table "entities"
        and the table "attributes".

        This view provides attribute values with
        the "positional" information kept in the entities tables, such as
        line number, level and order in the source file as well as groupname of
        the attribute ("ls", "attr", etc.)
        and timestamps for updates and indexing.
        """

        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("eattributes")

        entity = Entity.__table__
        attribute = Attribute.__table__
        attr_entity = aliased(Entity.__table__)
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
                entity.c.extra_info.label("e_extra_info"),
                attribute.c.id.label("attr_id"),
                attribute.c.entity.label("entity"),
                attribute.c.the_type.label("the_type"),
                attribute.c.the_value.label("the_value"),
                attribute.c.the_date.label("the_date"),
                attribute.c.obs.label("aobs"),
                attr_entity.c.extra_info.label("a_extra_info"),
            ).select_from(
                entity.join(attribute, entity.c.id == attribute.c.entity).join(
                    attr_entity, attribute.c.id == attr_entity.c.id
                )
            ),
        )
        # with eng.begin() as con:
        #     try:
        #         metadata.create_all(con)
        #     except Exception as exc:
        #         logging.error(f"Error creating view: {exc}")
        return attr

    def _create_named_entity_view(self):
        """Create a vue for entities with names

        persons, objects and geoentities

        """
        metadata: MetaData = self.metadata

        # We should have a class "named_entity" to mixin
        #  and detect dynamically.

        person = Person.__table__
        object = Object.__table__
        geoentity = Geoentity.__table__
        entity = Entity.__table__
        sel1 = select(
            person.c.id.label("id"),
            person.c.name.label("name"),
        )
        sel2 = select(
            object.c.id.label("id"),
            object.c.name.label("name"),
        )
        sel3 = select(
            geoentity.c.id.label("id"),
            geoentity.c.name.label("name"),
        )
        union_all = union(sel1, sel2, sel3).subquery()

        named_entities = views.view(
            "named_entities",
            metadata,
            select(
                entity.c.id.label("id"),
                entity.c.groupname.label("groupname"),
                entity.c["class"].label("pom_class"),
                entity.c.the_line.label("the_line"),
                entity.c.the_level.label("the_level"),
                entity.c.the_order.label("the_order"),
                entity.c.updated.label("updated"),
                entity.c.indexed.label("indexed"),
                entity.c.extra_info.label("extra_info"),
                union_all.c.name.label("name"),
            ).select_from(entity.join(union_all, entity.c.id == union_all.c.id)),
        )
        # with eng.begin() as con:
        #     try:
        #         metadata.create_all(con)
        #     except Exception as exc:
        #         logging.error(f"Error creating view: {exc}")
        return named_entities

    def _create_nfunction_view(self):
        """Create a vue that links people to acts through functions"""
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("nfuncs")

        named_entity = self.views["named_entities"]
        act = Act.__table__  # this can be replaced by aliased(Act) and get the full act with entity info
        relation = Relation.__table__
        nfuncs = views.view(
            "nfunctions",
            metadata,
            select(
                named_entity.c.id.label("id"),
                named_entity.c.name.label("name"),
                named_entity.c.groupname.label("groupname"),
                named_entity.c.pom_class.label("pom_class"),
                named_entity.c.the_line.label("the_line"),
                named_entity.c.the_level.label("the_level"),
                named_entity.c.the_order.label("the_order"),
                named_entity.c.updated.label("updated"),
                named_entity.c.indexed.label("indexed"),
                named_entity.c.extra_info.label("extra_info"),
                relation.c.the_value.label("func"),
                act.c.id.label("id_act"),
                act.c.the_type.label("act_type"),
                act.c.the_date.label("act_date"),
                act.c.obs.label("act_obs"),
            )
            .select_from(
                named_entity.join(relation, named_entity.c.id == relation.c.origin).join(
                    act, relation.c.destination == act.c.id
                )
            )
            .where(relation.c.the_type == "function-in-act"),
        )
        # with eng.begin() as con:
        #     try:
        #         metadata.create_all(con)
        #     except Exception as exc:
        #         logging.error(f"Error creating view: {exc}")
        return nfuncs

    def _create_nrelations_view(self):
        """A view that links relations with named entities.

        Easy access to the names of the entities involved in the
        relation. Depends on view name_entity_view for definition
        of what named entity is.

        Inspired by MHK nrels view

        .. code-block:: sql
            CREATE VIEW nrels AS
                SELECT
                    relations.id,
                    p1.id   AS ida,
                    p1.name AS namea,
                    p1.sex  as sexa,
                    p2.id   AS idb,
                    p2.name AS nameb,
                    p2.sex  AS sexb,
                    relations.the_type,
                    relations.the_value,
                    relations.the_date,
                    relations.obs
                FROM relations, persons p1, persons p2
                WHERE relations.origin = p1.id
                    AND relations.destination = p2.id
                    AND relations.the_type <> 'Identification';

        """
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("nrelations")
        origin = self.views["named_entities"]
        destination = aliased(origin)
        relation = self.get_table("relations")
        nrelations = views.view(
            "nrelations",
            metadata,
            select(
                relation.c.id.label("relation_id"),
                origin.c.id.label("origin_id"),
                origin.c.name.label("origin_name"),
                destination.c.id.label("destination_id"),
                destination.c.name.label("destination_name"),
                relation.c.the_type.label("relation_type"),
                relation.c.the_value.label("relation_value"),
                relation.c.the_date.label("relation_date"),
            ).select_from(
                relation.join(origin, relation.c.origin == origin.c.id).join(
                    destination, relation.c.destination == destination.c.id
                )
            ),
        )
        # with eng.begin() as con:
        #     try:
        #         metadata.create_all(con)
        #     except Exception as exc:
        #         logging.error(f"Error creating view: {exc}")
        return nrelations

    #
    # Builtin queries
    #
    def select(self, sql, session=None, as_dataframe=False):
        """Executes a select statement in the database
        Args:
            sql: sqlAlchemy select statement
        Returns:
            result: sqlAlchemy result object
        """
        # if sql is a string build a select statement
        if isinstance(sql, str):
            sql = select(text(sql))
        # if sql is a select statement
        elif not isinstance(sql, select):
            raise ValueError("sql must be a select statement or a string with a valid select statement")

        if session is None:
            with self.session() as session:
                try:
                    result = session.execute(sql)
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error executing select: {e}")
                    raise
        else:
            try:
                result = session.execute(sql)
            except Exception as e:
                session.rollback()
                logging.error(f"Error executing select: {e}")
                raise
        if as_dataframe:
            try:
                result = pd.DataFrame(result.fetchall(), columns=result.keys())
            except Exception as e:
                session.rollback()
                logging.error(f"Error converting to dataframe: {e}")
                raise
        else:
            return result

    def query(self, query_spec):
        """Executes a query in the database

        Args:
            query: sqlAlchemy query"""

        with self.session() as session:
            try:
                result = session.execute(query_spec)
            except Exception as e:
                session.rollback()
                logging.error(f"Error executing query: {e}")
                raise
        return result

    def get_person(self, *args, **kwargs):
        """Fetch a person by id

        See :func:`timelink.api.models.person.get_person`

        """
        if kwargs.get("session", None) is None and kwargs.get("db", None) is None:
            kwargs["db"] = self
        return timelink.api.models.person.get_person(*args, **kwargs)

    def get_entity(self, id: str, session=None) -> Entity:
        """Fetch an entity by id.

        See: :func:`timelink.api.models.entity.Entity.get_entity`

        """
        if session is None:
            with self.session() as session:
                try:
                    return Entity.get_entity(id, session)
                except Exception as e:
                    session.rollback()
                    logging.error(f"Error fetching entity: {e}")
                    raise
        else:
            return Entity.get_entity(id, session)

    #
    # Export and output
    #
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
            kleio_group ([type]): initial kleio group
            source_group ([type]): source group
            act_group ([type]): act group
        """

        with open(filename, "w", encoding="utf-8") as f:
            if kleio_group is not None:
                f.write(f"{kleio_group}\n")
            if source_group is not None:
                f.write(f"{source_group}\n")
            if act_group is not None:
                f.write(f"{act_group}\n")
            for id in ids:
                with self.session() as session:
                    try:
                        ent = Entity.get_entity(id, session)
                        f.write(str(ent.to_kleio()) + "\n\n")
                    except Exception as e:
                        session.rollback()
                        logging.error(f"Error exporting entity {id}: {e}")

    def pperson(self, id: str, session=None):
        """Prints a person in kleio notation"""
        if session is None:
            session = self.session()
            p = self.get_person(id=id, session=session)
            # get session from object p
            kleio = p.to_kleio()
        else:
            p = self.get_person(id=id, session=session)
            kleio = p.to_kleio()
        print(kleio)

    def as_schema(self) -> TimelinkDatabaseSchema:
        """Return a Pydantic schema for this database"""
        return TimelinkDatabaseSchema(db_name=self.db_name, db_type=self.db_type)
