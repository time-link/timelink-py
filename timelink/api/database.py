""" Database connection and setup

TODO:

- use logging to database functions.
- add mysql support


"""

# pylint: disable=unused-import
import os
import time
import warnings
import logging

from typing import List
from pydantic import TypeAdapter

from sqlalchemy import Engine
from sqlalchemy import MetaData
from sqlalchemy import Table
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import select, func, union
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy.orm import aliased
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import create_database
from sqlalchemy.sql.selectable import TableClause

import timelink
from timelink import migrations
from timelink.api.models.act import Act
from timelink.api.models.geoentity import Geoentity
from timelink.api.models.object import Object
from timelink.mhk import utilities
from timelink import models  # pylint: disable=unused-import
from timelink.api.models.base_class import Base
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

    Main methods:
        * table_names: get the current tables in the database
        * get_columns: get the columns for a table or model
        * table_row_count: get the number of rows of each table in the database
        * get_models: get ORM Models for using in Queries
        * create_db: create the database tables and views
        * drop_db: drop all timelink related tables from the database
        * get_imported_files: get the list of imported files in the database
        * get_import_status: get the import status of the kleio files
        * update_from_sources: update the database from the sources
        * query: execute a query in the database
        * get_person: fetch a person by id
        * get_entity: fetch an entity by id
        * export_as_kleio: export entities to a kleio file
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

        self.engine = create_engine(self.db_url, connect_args=connect_args)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.metadata = models.Base.metadata
        # create an empty database if it does not exist
        if not database_exists(self.engine.url):  # noqa
            try:
                create_database(self.engine.url)
                self.create_db()
            except Exception as exc:
                logging.error(exc)
                raise Exception("Error while creating database") from exc
        # if the database exists, check if the tables are there
        elif self.table_exists("entities") is False:
            self.create_db()
        else:  # the database exists upgrade if necessary
            try:
                migrations.upgrade(self.db_url)
                with self.session() as session:
                    self.ensure_all_mappings(
                        session
                    )  # this will cache the pomsom mapper objects
                # ensure views
                self.create_views()
            except Exception as exc:
                logging.error(exc)

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

        self.create_tables()
        with self.session() as session:
            session.commit()
            session.rollback()
            session.expire_on_commit = False
            self.load_database_classes(session)
            self.ensure_all_mappings(session)
            session.commit()
        try:
            migrations.stamp(self.db_url, "head")
        except Exception as exc:
            logging.error(exc)
        try:
            # self.create_views()
            pass
        except Exception as exc:
            logging.error(exc)
            raise Exception("Error while creating database views") from exc

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
        self.create_views()
        self.metadata.create_all(self.engine)  # only creates if missing

    def create_views(self):
        """Creates the views

        eattributes: view of the entity attributes linked with entity information
        pattributes: view of the person attributes linked with person information
        named_entities: view of the named entities linked with entity information
        nfunctions: view of the functions of people in acts linked with entity information
        See issue #63
        :return: None
        """
        self.pattribute_view = self.create_pattribute_view()
        self.eattribute_view = self.create_eattribute_view()
        self.named_entity_view = self.create_named_entity_view()
        self.nfunctions_view = self.create_nfunction_view()

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
                length = session.scalar(
                    select(func.count()).select_from(  # pylint: disable=not-callable
                        text(table)
                    )  # pylint: disable=not-callable
                )  # pylint: disable=not-callable
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
        # If any of the core tables are missing, create all tables based on ORM metadata
        # NOTE: tables are not created based on the pom_som_base_mappings definitions
        # because the ORM metadata is the source of truth

        if len(missing) > 0:
            self.create_tables()  # ORM metadata trumps pom_som_base_mappings

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

        stmt = select(Entity.pom_class, Entity.groupname).distinct()
        results = session.execute(stmt).all()
        for pom_class, groupname in results:
            if groupname is not None:
                gname = groupname
            else:
                gname = "class"

            Entity.group_models[gname] = Entity.get_orm_for_pom_class(pom_class)

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

    def drop_db(self, session=None):
        """
        This will drop all timelink related tables from the database.
        It will not touch non timelink tables that might exist.

        If a real drop database is desidered use sqlalchemy_utils.drop_database
        :param session:

        """
        if session is None:
            session = self.session()

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
                    "Empty list of files. \n"
                    "Either provide list of files or attach database to Kleio server."
                )
            else:
                kleio_files = self.get_kleio_server().get_translations(
                    path=path, recurse=recurse
                )
        files: List[KleioFile] = get_import_status(
            self, kleio_files=kleio_files, match_path=match_path
        )
        if status is not None:
            files = [file for file in files if file.import_status.value == status]
        return files

    def get_need_import(  # TODO: better name check_need_import
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

        kleio_files: List[KleioFile] = get_import_status(
            self, kleio_files, match_path=match_path
        )
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
        recurse=True,
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
            recurse (bool, optional): if True, recurse the path; defaults to True.
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
            for kfile in self.kserver.get_translations(
                path=path, recurse=recurse, status="T"  # TODO: make parameter
            ):
                logging.info(
                    "Request translation of %s %s", kfile.status.value, kfile.path
                )
                self.kserver.translate(kfile.path, recurse="no", spawn="no")
            # wait for translation to finish
            logging.debug("Waiting for translations to finish")
            pfiles = self.kserver.get_translations(path=path, recurse="yes", status="P")

            qfiles = self.kserver.get_translations(path=path, recurse="yes", status="Q")
            # TODO: change to import as each translation finishes
            while len(pfiles) > 0 or len(qfiles) > 0:
                time.sleep(1)

                pfiles = self.kserver.get_translations(
                    path="", recurse="yes", status="P"
                )
                qfiles = self.kserver.get_translations(
                    path="", recurse="yes", status="Q"
                )
            # import the files
            to_import = self.kserver.get_translations(
                path=path, recurse=recurse, status="V"  # TODO recurse make param
            )
            if with_translation_warnings:
                to_import += self.kserver.get_translations(
                    path=path, recurse=recurse, status="W"
                )
            if with_translation_errors:
                to_import += self.kserver.get_translations(
                    path=path, recurse=recurse, status="E"
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
                        logging.info("Importing %s", kfile.path)
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
                        logging.debug("Imported %s: %s", kfile.path, stats)
                        time.sleep(1)
                    except Exception as e:
                        logging.error("Unexpected error:")
                        logging.error("Error: %s", e)
                        continue

    def query(self, query_spec):
        """Executes a query in the database

        Args:
            query: sqlAlchemy query"""

        with self.session() as session:
            result = session.query(query_spec)
        return result

    def get_person(self, *args, **kwargs):
        """Fetch a person by id

        See :func:`timelink.api.models.person.get_person`

        """
        if "db" not in kwargs and "session" not in kwargs:
            kwargs["db"] = self
        return timelink.api.models.person.get_person(*args, **kwargs)

    def get_entity(self, id: str, session=None) -> Entity:
        """Fetch an entity by id.

        See: :func:`timelink.api.models.entity.Entity.get_entity`

        """
        if session is None:
            with self.session() as session:
                return Entity.get_entity(id, session)
        else:
            return Entity.get_entity(id, session)

    def pperson(self, id: str):
        """Prints a person in kleio notation"""
        print(self.get_person(id=id).to_kleio())

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
                return [
                    self.get_model_by_name(c, make_alias=make_alias) for c in class_id
                ]
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

    def get_table(self, table_or_class: str | Entity) -> Table:
        """Get a table object from the database

        Args:
            table_or_class (str | Entity): table name, model name of ORM model

        Returns:
            sqlAlchemy Table: table object


        """
        if type(table_or_class) is str:
            model = self.get_model(table_or_class)
            if model is not None:
                return model.__table__
            elif table_or_class in self.table_names():
                table = self.metadata.tables.get(table_or_class, None)
                if table is not None:
                    return table
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
            if class_or_table in self.table_names():
                return list(self.get_table(class_or_table).columns)
            else:
                raise ValueError(f"{class_or_table} not found")

        insp = inspect(Model)
        return list(insp.columns)

    def describe(self, argument, show=None, **kwargs):
        """Describe a table or a model
          if argument is a string, it is assumed to be a table
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
        if isinstance(argument, str):
            columns = self.get_columns(argument)
        elif isinstance(argument, type) and issubclass(argument, Base):
            Model = argument
            insp = inspect(Model)
            columns = list(insp.columns)
        elif issubclass(type(argument), TableClause):
            columns = list(argument.columns)

        if len(columns) > 0 and show is not None:
            print(str(argument))
            for col in columns:
                fkey = str(col.foreign_keys) if col.foreign_keys else ""
                print(f"{col.name:<20} {str(col.table):<20} {str(col.type):<10} {fkey}")
        return columns

    def create_pattribute_view(self):
        """Return the pattribute view.

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
            ).select_from(person.join(attribute, person.c.id == attribute.c.entity)),
        )
        with eng.begin() as con:
            metadata.create_all(con)
        return attr

    def create_eattribute_view(self):
        """Return the eattribute view.

        Returns a sqlalchemy table with a view that joins the table "entities"
        and the table "attributes".

        This view provides attribute values with
        the "positional" information kept in the entities tables, such as
        line number, level and order in the source file as well as groupname of
        the attribute ("ls", "attr", etc.)
        and timestamps for updates and indexing.
        """

        eng: Engine = self.engine
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
        with eng.begin() as con:
            metadata.create_all(con)
        return attr

    def create_named_entity_view(self):
        """Create a vue for entities with names

        persons, objects and geoentities

        """
        eng: Engine = self.engine
        metadata: MetaData = self.metadata

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
                entity.c['class'].label("pom_class"),
                entity.c.the_line.label("the_line"),
                entity.c.the_level.label("the_level"),
                entity.c.the_order.label("the_order"),
                entity.c.updated.label("updated"),
                entity.c.indexed.label("indexed"),
                entity.c.extra_info.label("extra_info"),
                union_all.c.name.label("name")
            ).select_from(entity.join(union_all, entity.c.id == union_all.c.id)),
        )
        with eng.begin() as con:
            metadata.create_all(con)
        return named_entities

    def create_nfunction_view(self):
        """Create a vue that links people to acts through functions

        TODO: this should be generalized to objects (named entities)
        """
        eng: Engine = self.engine
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("nfuncs")

        named_entity = self.named_entity_view
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
        with eng.begin() as con:
            metadata.create_all(con)
        return nfuncs

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
                    ent = Entity.get_entity(id, session)
                    f.write(str(ent.to_kleio()) + "\n\n")

    def table_exists(self, table_name: str) -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name)
