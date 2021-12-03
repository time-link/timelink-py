import pytest
from sqlalchemy.orm import Session, sessionmaker

from timelink.kleio.groups import KKleio, KSource, KAct, KAbstraction, KPerson, \
    KLs, KAtr, KGroup, KElement
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.entity import Entity  # noqa
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.db_system import DBSystem
# Session is shared by all tests
from tests import Session


DBSystem.conn_string = 'sqlite:///test_db'


@pytest.fixture(scope="module")
def dbsystem():
    db = DBSystem(DBSystem.conn_string)
    Session.configure(bind=db.engine())
    with Session() as session:
        db.load_database_classes(session)
    yield db
    db.drop_db()


def test_create_db(dbsystem):
    # Database is created and initialized in the fixture
    metadata = Base.metadata
    tables = list(metadata.tables.keys())
    assert len(tables) > 0, "tables where not created"

def test_ensure_mapping(dbsystem):
    with Session() as session:
        pom_classes = PomSomMapper.get_pom_classes(session=session)
        pom_ids = PomSomMapper.get_pom_class_ids(session=session)
        pom_tables = [pom_class.table_name for pom_class in pom_classes]
        pom_class: PomSomMapper
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session=session)
            #print(repr(pom_class))
            #print(pom_class)
        orm_mapped_classes = Entity.get_som_mapper_to_orm_as_dict()
        non_mapped = set(pom_ids) - set(orm_mapped_classes.keys())
        assert len(non_mapped) == 0, "Not all classes are mapped to ORM"
        orm_mapped_tables = Entity.get_tables_to_orm_as_dict()
        tables_not_mapped = set(pom_tables) - set(orm_mapped_tables)
        assert len(tables_not_mapped) == 0, "Not all class tables are mapped in ORM"
        db_tables = dbsystem.table_names()
        tables_not_in_db = set(orm_mapped_tables) - set (db_tables)
        assert len(tables_not_in_db) == 0, "Not all mapped tables were created in the db"

def test_store_KGroup_1(dbsystem):
    kfonte: KGroup = KGroup.extend('fonte',
                                   position=['id','data'],
                                   also=['tipo',
                                         'ano',
                                         'obs',
                                         'substitui'])
    afonte = kfonte('f001',
                    data=KElement('data','2021-12-02',element_class='date'),
                    tipo=KElement('tipo','teste',element_class='type'))
    with Session() as session:
        session.rollback()
        session.flush()
        source_class: PomSomMapper = PomSomMapper.get_pom_class('source',session)
        afonte._pom_class_id = source_class.id # need a set_mapper method
        source_class.store_KGroup(afonte,session)
        session.commit()
        same_fonte = session.get(source_class,afonte.id)
        print(same_fonte)







