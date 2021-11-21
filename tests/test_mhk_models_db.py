import pytest
from sqlalchemy.orm import Session

from timelink.mhk.models import base  # noqa
from timelink.mhk.models.entity import Entity  # noqa
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.db_system import DBSystem


DBSystem.conn_string = 'sqlite:///teste_db'

@pytest.fixture(scope="module")
def dbsystem():
    db = DBSystem()
    db.init_db(DBSystem.conn_string)
    yield db
    db.db_drop()


def test_create_db(dbsystem):
    # Database is created and initialized in the fixture
    metadata = Base.metadata
    tables = list(metadata.tables.keys())

    assert len(tables) > 0, "tables where not created"

def teste_ensure_mapping(dbsystem):
    session: Session
    with Session(dbsystem.engine) as session:
        pom_classes = PomSomMapper.get_pom_classes(session=session)
        pom_ids = PomSomMapper.get_pom_class_ids(session=session)
        pom_tables = [pom_class.table_name for pom_class in pom_classes]
        pom_class: PomSomMapper
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session=session)
            print(repr(pom_class))
            print(pom_class)
        orm_mapped_classes = Entity.get_spmapper_to_orm_as_dict()
        non_mapped = set(pom_ids) - set(orm_mapped_classes.keys())
        assert len(non_mapped) == 0, "Not all classes are mapped to ORM"
        orm_mapped_tables = Entity.get_tables_to_orm_as_dict()
        tables_not_mapped = set(pom_tables) - set(orm_mapped_tables)
        assert len(tables_not_mapped) == 0, "Not all class tables are mapped in ORM"
        db_tables = dbsystem.table_names()
        tables_not_in_db = set(orm_mapped_tables) - set (db_tables)
        assert len(tables_not_in_db) == 0, "Not all mapped tables were created in the db"










