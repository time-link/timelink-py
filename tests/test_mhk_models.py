from timelink.mhk.models import entity
from sqlalchemy import MetaData, create_engine
from timelink.mhk.models.base_class import Base
from timelink.mhk.models import base # noqa

import pytest

class DBSystem:
    connection = None
    engine = None
    conn_string = None
    metadata: MetaData = None

    def db_init(self, conn_string):
        self.engine = create_engine(conn_string or self.conn_string)
        self.metadata = Base.metadata
        self.metadata.create_all(bind=self.engine)
        self.connection = self.engine.connect()

    def db_drop(self):
        self.metadata.drop_all(bind=self.engine)


DBSystem.conn_string = 'sqlite:///teste_db'

@pytest.fixture(scope="module")
def dbsystem():
    db = DBSystem()
    db.db_init(DBSystem.conn_string)
    yield db
    db.db_drop()


def test_create_db(dbsystem):
    pass











