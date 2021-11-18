from typing import List

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

def test_populate_entity_class(dbsystem):
    session: Session


    with Session(dbsystem.engine) as session:
        orm_mapped_classes = Entity.pom_class_to_orm()
        orm_mapped_tables = Entity.table_to_orm()
        db_tables = list(Entity.metadata.tables.keys())
        pom_classes = PomSomMapper.get_pom_classes(session=session)
        pom_ids = PomSomMapper.get_pom_class_ids(session=session)
        pom_class: PomSomMapper
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session=session)
            print(repr(pom_class))
            print(pom_class)









