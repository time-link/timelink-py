from warnings import warn

from sqlalchemy import engine, create_engine, select, inspect, MetaData
from sqlalchemy.orm import sessionmaker

from timelink.mhk.models import base  # noqa
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.base_mappings import pom_som_base_mappings
from timelink.mhk.models.pom_som_mapper import PomSomMapper

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

    def __init__(self, conn_string=None, sql_echo=False):
        """
        For the interaction of "engine" and "session" alternative
        configurations see
        https://docs.sqlalchemy.org/en/14/orm/session_basics.html

        :param conn_string: a sqlalchemy connection URL, str.
        """

        self.init_db(conn_string, sql_echo)

    def init_db(self, conn_string, sql_echo=False):
        """
        Create an engine from a connection string.
        Check if database is properly setup up
        by creating core tables, PomSomMappers
        and ORM classes. Database should be ready
        for import after this method is called.

        :param conn_string: SQLAlchemy connection string
        :param sql_echo: bool if True echo sql statements
        :return:
        """

        if conn_string is not None:
            self.db_engine = create_engine(
                conn_string or self.conn_string, future=True, echo=sql_echo
            )
            self.conn_string = conn_string

        if self.conn_string is None:
            raise ValueError("No connection string available")

        self.metadata = Base.metadata
        self.metadata.bind = self.db_engine

        with self.get_session() as session:
            self.load_database_classes(session)
            self.ensure_all_mappings(session)
            session.commit()

    def get_engine(self) -> engine:
        """Return sqlalchemy engine"""
        return self.db_engine

    def engine(self) -> engine:
        """DEPRECATED use TimelinkDB.get_engine()"""
        warn("This method is deprecated, use get_engine()", DeprecationWarning,
             stacklevel=2)
        return self.get_engine()

    def get_session(self):
        """Get a session maker binded to this engine

        Example:

            with db.get_sesssionmaker() as session:

        """
        Session = sessionmaker(bind=self.db_engine)  # noqa
        return Session()

    def get_metadata(self):
        """ Get the metadata associated with this engine

        Not sure this is done right. We probably need to create the models
        without inheriting from Base and instead use imperative_mapping
        https://docs.sqlalchemy.org/en/14/orm/mapping_styles.html#imperative-a-k-a-classical-mappings  # noqa
        and
        https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#setting-up-the-registry # noqa

        See Also:
            * https://gist.github.com/pawl/9935333
            * https://www.oreilly.com/library/view/essential-sqlalchemy/9780596516147/ch01.html  # noqa
            * https://stackoverflow.com/questions/58598098
            """
        return self.metadata

    def create_tables(self):
        """
        Creates the tables from the current ORM metadata if needed

        :return: None
        """
        self.get_metadata().create_all(self.db_engine)  # only creates if missing

    def load_database_classes(self, session):
        """
        Populates database with core Database classes
        :param session:
        :return:
        """

        # Check if the core tables are there
        existing_tables = self.table_names_in_db()
        base_tables = [v[0].table_name for v in pom_som_base_mappings.values()]
        missing = set(base_tables) - set(existing_tables)
        if len(missing) > 0:
            self.create_tables()

        # check if we have the data for the core database entity classes
        stmt = select(PomSomMapper.id)
        available_mappings = session.execute(stmt).scalars().all()
        for k in pom_som_base_mappings.keys():
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

    def table_names_in_db(self):
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
        Base.metadata.drop_all(self.db_engine)
