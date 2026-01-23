"""Database connection and setup

This module provides the TimelinkDatabase class, which manages the connection
to a Timelink database and provides high-level methods for database operations.
The class integrates several mixins to provide specialized functionality for
PostgreSQL, SQLite, Kleio server integration, metadata inspection, and querying.
"""

import logging
import os
import warnings
from collections import defaultdict

from sqlalchemy import (
    create_engine,
    select,
    text,
)
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy_utils import create_database, database_exists, drop_database

from timelink import models  # pylint: disable=unused-import
from timelink import migrations
from timelink.api.models import (
    Entity,
    PomSomMapper,
    pom_som_base_mappings,
)
from timelink.api.models.base_class import Base
from timelink.kleio import KleioServer
from timelink.mhk import utilities

from . import views  # see https://github.com/sqlalchemy/sqlalchemy/wiki/Views
from .database_postgres import (
    get_postgres_container,
    get_postgres_container_user,
    get_postgres_container_pwd,
    get_postgres_dbnames,
    get_postgres_url,
    is_postgres_running,
    is_valid_postgres_db_name,
    start_postgres_server,
)
from .database_sqlite import (
    get_sqlite_databases,
    get_sqlite_url,
)
from .database_utils import get_db_password, get_import_status, random_password
from .database_views import DatabaseViewsMixin
from .database_metadata import DatabaseMetadataMixin
from .database_kleio import DatabaseKleioMixin
from .database_query import DatabaseQueryMixin, TimelinkDatabaseSchema


__all__ = [
    "TimelinkDatabase",
    "TimelinkDatabaseSchema",
    "get_postgres_container",
    "get_postgres_container_user",
    "get_postgres_container_pwd",
    "get_postgres_dbnames",
    "get_postgres_url",
    "is_postgres_running",
    "is_valid_postgres_db_name",
    "start_postgres_server",
    "get_sqlite_databases",
    "get_sqlite_url",
    "get_db_password",
    "get_import_status",
    "random_password",
]


class TimelinkDatabase(
    DatabaseViewsMixin,
    DatabaseMetadataMixin,
    DatabaseKleioMixin,
    DatabaseQueryMixin,
):
    """Database connection and setup

    Creates a database connection and session. If the database does not exist,
    it is created. **db_type** determines the type of database.

    Currently, only sqlite and postgres are supported.

    * If db_type is sqlite, the database is created in the current directory.
    * If db_type is postgres or mysql, the database is created in a docker container.
    * If the database is postgres, the container is named timelink-postgres.
    * If the database is mysql, the container is named timelink-mysql.

    This class inherits from several mixins:
    - DatabaseViewsMixin: Management of database views.
    - DatabaseMetadataMixin: Inspection of database metadata and ORM models.
    - DatabaseKleioMixin: Integration with Kleio server for data imports.
    - DatabaseQueryMixin: High-level data access and querying methods.

    Attributes:
        db_url (str): database sqlalchemy url
        db_name (str): database name
        db_user (str): database user (only for postgres databases)
        db_pwd (str): database password (only for postgres databases)
        engine (Engine): database engine
        session (Session): database session factory
        metadata (MetaData): database metadata
        db_container (Container): database docker container (for postgres/mysql)
        kserver (KleioServer): kleio server attached to this database, used for imports
    """

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

        Example::

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
                    pwd = [var for var in container_vars if "POSTGRES_PASSWORD" in var][
                        0
                    ]
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
        if (
            not database_exists(self.engine.url) or db_url == "sqlite:///:memory:"
        ):  # noqa
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
                    self._ensure_all_mappings(
                        session
                    )  # this will cache the pomsom mapper objects
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
        """Create the database tables, views, and mappings.

        This method performs the following operations:
        1. Cleans caches of Mappings and ORM classes.
        2. Removes dynamic tables from metadata.
        3. Creates tables from ORM metadata.
        4. Stamps the database with the most recent Alembic version.
        5. Loads database classes and ensures all mappings are available.
        6. Creates database views for common queries.

        Raises:
            Exception: If there is an error creating the database or updating views.
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
        """Check the database health and integrity.

        This method verifies that:
        1. All required ORM tables exist in the database.
        2. Missing tables are created if needed.
        3. For PostgreSQL, checks for and removes obsolete 'linkstatus' type.

        If missing tables are detected, they are created automatically.
        """
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
                    select(text("1")).where(
                        text(
                            "EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linkstatus')"
                        )
                    )
                )
                if result.scalar() is not None:
                    logging.warning("link_status found, deleting it")
                    result = connection.execute(
                        text("DROP TYPE IF EXISTS link_status CASCADE")
                    )
                    # result = connection.execute(
                    #     text("CREATE TYPE link_status AS ENUM ('valid', 'invalid', 'possible')")
                    # )

    def _build_dependency_graph(self, tables):
        """Build a dependency graph of tables based on foreign key constraints.

        This method analyzes the foreign key relationships between tables
        to create a directed graph representing table dependencies.

        Args:
            tables (list): List of SQLAlchemy Table objects.

        Returns:
            defaultdict: A dictionary where keys are table names and values are sets
                        of table names that each table depends on.

        Note:
            This code was generated by GitHub Copilot.
        """
        graph = defaultdict(set)
        for table in tables:
            for fk in table.foreign_keys:
                graph[table.name].add(fk.column.table.name)
        return graph

    def _topological_sort(self, graph):
        """Perform topological sort on the dependency graph using Kahn's algorithm.

        Topological sort orders nodes in a directed acyclic graph (DAG) such that
        for every directed edge from node A to node B, node A appears before node B
        in the ordering. In our case, nodes are tables and directed edges represent
        foreign key dependencies.

        Args:
            graph (dict): Dependency graph where keys are table names and values
                         are sets of dependencies.

        Returns:
            list: List of table names in topologically sorted order.

        Raises:
            ValueError: If a circular dependency is detected in the database schema.

        Note:
            This implementation uses Kahn's algorithm for topological sorting.
            Code was generated by GitHub Copilot.
        """
        in_degree = defaultdict(int)  # Count incoming edges for each node
        for table, dependencies in graph.items():
            for dependency in dependencies:
                if dependency != table:
                    in_degree[table] += 1

        queue = [
            table for table in graph if in_degree[table] == 0
        ]  # Start with nodes with no incoming edges
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
        """Create tables from the current ORM metadata if needed.

        This method creates all tables defined in the SQLAlchemy ORM metadata
        that inherit from timelink.api.models.Base. It is typically called after
        an empty database is created to populate it with the basic tables associated
        with builtin ORM Models.

        Raises:
            Exception: If there is an error creating the tables.
        """
        try:
            self.metadata.create_all(self.engine)
        except Exception as exc:
            logging.error(f"Error creating tables: {exc}")
            raise exc

    def _drop_views(self):
        """Drop all existing database views managed by Timelink.

        Iterates through the list of view names currently in the database
        and issues DROP VIEW statements for those identified as Timelink views.
        """

        existing = self.view_names()
        with self.session() as session:
            try:
                for view_name in existing:
                    stmt = views.DropView(view_name).execute_if(
                        callable_=views.view_exists
                    )
                    session.execute(stmt)
                    session.commit()
            except Exception as exc:
                session.rollback()
                logging.error(f"Error dropping view {view_name}: {exc}")

    def _create_views(self):
        """Create standard database views for common queries.

        Creates the following views:
        - nattributes: Entity attributes linked with entity information.
        - eattributes: Person/entity attributes with positional information from source files.
        - named_entities: Named entities (persons, objects, geoentities) with unified interface.
        - nfunctions: Functions of people in acts with entity information.
        - nrelations: Relations between named entities with origin and destination names.

        These views simplify common queries by joining frequently accessed tables.

        Raises:
            Exception: If there is an error creating the views.

        See Also:
            Issue #63 in the project repository for more details on view requirements.
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
        """Drop and recreate all database views.

        This method ensures that views reflect the current state of the database
        schema by dropping existing views and recreating them.
        """
        self._drop_views()
        self._create_views()

    def has_active_connections(self):
        """Check if there are active connections in the engine pool."""
        if hasattr(self.engine, "pool"):
            # Check if there are checked out connections
            return self.engine.pool.checkedout() > 0
        return False

    def drop_db(self, session=None, timelink_only=False):
        """Drop the database or only the Timelink-related tables.

        Args:
            session (Session, optional): Database session to use. Defaults to None.
            timelink_only (bool, optional): If True, only drop Timelink-related tables and views
                                            while leaving other tables intact. If False,
                                            drops the entire database. Defaults to False.

        Note:
            For PostgreSQL, this method attempts to terminate other active connections
            before dropping the database to avoid "database is being accessed by other users" errors.
        """

        if not timelink_only:
            if ":memory:" not in self.db_url:
                if session is not None:
                    session.close()
                if self.engine:
                    import time

                    time.sleep(0.1)
                    # For PostgreSQL, you might want to terminate connections first
                    if self.engine.url.drivername.startswith("postgresql"):
                        with self.engine.connect() as conn:
                            # Need autocommit for drop database operations
                            conn.execution_options(isolation_level="AUTOCOMMIT")
                            conn.execute(
                                text(
                                    "SELECT pg_terminate_backend(pid) "
                                    "FROM pg_stat_activity "
                                    "WHERE datname = :dbname AND pid <> pg_backend_pid()"
                                ),
                                {"dbname": self.db_name},
                            )
                self.engine.dispose()
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

    def _load_database_classes(self, session):
        """Populate the database with core Timelink classes and mappings.

        Ensures that core tables exist and populates the PomSomMapper table
        with builtin mappings if they are missing.

        Args:
            session (Session): An active database session.
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

    def _ensure_all_mappings(self, session):
        """Ensure that all database classes have corresponding tables and ORM mappings.

        This method:
        1. Iterates through all PomSomMapper objects and ensures their mappings are established.
        2. Handles dynamic pom_classes by setting them as dynamic if necessary.
        3. Removes dynamic tables from metadata that are not present in the current database.
        4. Clears and repopulates the group models cache by introspecting existing entities.

        Args:
            session (Session): An active database session.
        """

        pom_classes = PomSomMapper.get_pom_classes(session)
        for pom_class in pom_classes:
            pom_class = session.merge(pom_class)  # Ensure attached to session
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
