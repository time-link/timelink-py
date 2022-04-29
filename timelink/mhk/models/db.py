from typing import List
from warnings import warn

from sqlalchemy import MetaData, engine, create_engine, select, inspect, Table

from timelink.mhk.models import base, Session  # noqa
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.base_mappings import pom_som_base_mappings
from timelink.mhk.models.entity import Entity
from timelink.mhk.models.pom_som_mapper import PomSomMapper, PomClassAttributes

SQLALCHEMY_ECHO = False


class TimelinkDB:
    """
    Provide access to a Timelink-MHK database

    Example:

        from timelink.mhk.models import Session
        from timelink.mhk.model.db import TimelinkDB

        dbsys = TimelinkDB("sql alchemy connection string")



    """

    db_engine: engine = None
    db_name: str = None
    conn_string = None
    metadata: MetaData = None

    def __init__(self, conn_string=None, **extra_args):
        """
        For the interaction of "engine" and "session" alternative
        configurations see
        https://docs.sqlalchemy.org/en/14/orm/session_basics.html


        Args:
            conn_string: sqllchemy connection string
            **extra_args: passed on to sqlalchemy create engine
        """

        self.init_db(conn_string, **extra_args)

    def init_db(self, conn_string, **extra_args):
        """
        Create an engine from a connection string.
        Check if database is properly setup up
        by creating core tables, PomSomMappers
        and ORM classes. Database should be ready
        for import after this method is called.

        Args:
            conn_string: SQLAlchemy connection string
            **extra_args: arguments passed to create_engine

        Returns:
            None


        """

        if conn_string is not None:
            self.db_engine = create_engine(
                conn_string or self.conn_string, future=True, **extra_args
            )
            self.conn_string = conn_string
            self.metadata = Base.metadata

        if self.conn_string is None:
            raise ValueError("No connection string available")

        with Session(bind=self.db_engine) as session:
            self.create_tables(self.db_engine)
            session.commit()
            session.rollback()
            self.load_database_classes(session)
            self.ensure_all_mappings(session)
            1 + 1
            session.commit()
            2 + 2

    def get_engine(self) -> engine:
        """Return sqlalchemy engine"""
        return self.db_engine

    def engine(self) -> engine:
        """DEPRECATED use TimelinkDB.get_engine()"""
        warn("This method is deprecated, use get_engine()", DeprecationWarning,
             stacklevel=2)
        return self.get_engine()

    def get_metadata(self) -> MetaData:
        """Return sqlalchemy metadata"""
        return self.metadata

    def create_tables(self, bind, tables: List[Table] = []):
        """
        Creates the tables from the current ORM metadata if needed

        :return: None
        """
        meta_tables = self.get_metadata().tables
        core_tables = [
            meta_tables[Entity.__tablename__],
            meta_tables[PomSomMapper.__tablename__],
            meta_tables[PomClassAttributes.__tablename__]
        ]
        self.metadata.create_all(bind, tables=core_tables)  # creates if missing

    @staticmethod
    def load_database_classes(session):
        """
        Populates database with core Database classes

        :param session: a session to the database
        :return: None
        """

        # check if we have the data for the core database entity classes
        stmt = select(PomSomMapper.id)
        available_mappings = session.execute(stmt).scalars().all()
        for k in pom_som_base_mappings.keys():
            if k not in available_mappings:
                data = pom_som_base_mappings[k]
                session.bulk_save_objects(data)
        # this will cache the pomsom mapper objects
        session.commit()

    @staticmethod
    def ensure_all_mappings(session):
        """Ensure that all database classes have a table and ORM class"""
        pom_classes = PomSomMapper.get_pom_classes(session)
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session)

    def db_tables(self):
        """Current tables in the current database"""
        insp = inspect(self.db_engine)
        db_tables = insp.get_table_names()  # tables in the database
        return db_tables

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
        self.metadata = Base.metadata
        self.metadata.drop_all(self.db_engine)
