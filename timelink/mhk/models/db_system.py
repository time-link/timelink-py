from sqlalchemy import MetaData, engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from timelink.mhk.models import base  # noqa
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base_mappings import pom_som_base_mappings


SQLALCHEMY_ECHO=True

class DBSystem:
    """
    Provide access to a Timelink-MHK database

    Usage

    dbsys = DBSystem("sql alchemy connection string")



    """
    engine: engine = None
    conn_string = None
    session_class: Session = None
    metadata: MetaData = None

    def __init__(self, conn_string=None):
        """
        For the interaction of "engine" and "session" alternative
        configurations see
        https://docs.sqlalchemy.org/en/13/orm/session_basics.html

        :param conn_string: a sqlalchemy connection URL, str.
        """
        if conn_string is not None:
            self.set_engine_and_session(conn_string)

    def set_engine_and_session(self, conn_string):
        """
        Create an engine and session from a connection string.
        This is called by __init__ and should not be called again
        except if __init__ was called without a connection string.

            dbsys = DBSystem("sqlite:///test_db").

            session = dbsys.session()


            Session = dbsys.session_class
            session = Session()

            engine = dbsys.engine()

        :param conn_string:
        :return:
        """
        if conn_string is not None:
            self.engine = create_engine(conn_string
                                        or self.conn_string,
                                        future=True,echo=SQLALCHEMY_ECHO)
            self.session_class = sessionmaker(bind=self.engine)
            self.conn_string = conn_string


    def session(self):
        return self.session_class()

    def engine(self):
        return self.engine

    def create_db(self):
        """
        Creates a database from currently

        :return: None
        """

        self.metadata = Base.metadata
        self.metadata.create_all(bind=self.engine())  # only creates if missing
        with self.session() as session:
            self.load_base_mappings()
            PomSomMapper.ensure_all_mappings(bind=session)

    def get_engine(self, conn_string):
        return create_engine(conn_string or self.conn_string)

    def load_base_mappings(self):
        with self.session() as session:
            stmt = select(PomSomMapper.id)
            available_mappings = session.execute(stmt).scalars().all()
            for k in pom_som_base_mappings.keys():
                if k not in available_mappings:
                    data = pom_som_base_mappings[k]
                    session.bulk_save_objects(data)
                    session.commit()

    def table_names(self):
        return self.engine.table_names()

    def drop_db(self):
        with self.session() as session:
            self.metadata.drop_all(bind=session)
