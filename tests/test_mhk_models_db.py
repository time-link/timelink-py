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


DBSystem.conn_string = 'sqlite:///test_db?check_same_thread=False'


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


def test_entity_contains(dbsystem):
    ent1: Entity = Entity(id='e001')
    ent1.groupname = "entity"
    ent1.pom_class = 'entity'
    ent1.line = 1
    ent1.level = 1
    ent1.sequence = 1

    ent2: Entity = Entity(id='e002')
    ent2.groupname = "entity"
    ent2.pom_class = 'entity'
    ent2.line = 2
    ent2.level = 2
    ent2.sequence = 2
    ent1.contains.append(ent2)

    ent3: Entity = Entity(id='e003')
    ent3.groupname = "entity"
    ent3.pom_class = 'entity'
    ent3.line = 2
    ent3.level = 2
    ent3.sequence = 2
    ent1.contains.append(ent3)

    with Session() as session:
        session.add(ent1)
        session.add(ent2)
        session.add(ent3)
        ent4 = ent2.contained_by
        assert ent4 is ent1
        ent5 = ent1.contains[1]
        assert ent5 is ent3

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
        session.close()

def test_store_KGroup_1(dbsystem):
    kfonte: KGroup = KGroup.extend('fonte',
                                   position=['id','data'],
                                   also=['tipo',
                                         'ano',
                                         'obs',
                                         'substitui'])
    afonte = kfonte('f001',
                    data=KElement('data','2021-12-02',element_class='date'),
                    tipo=KElement('tipo','teste',element_class='type'),
                    obs="First group stored through ORM with non core group")
    with Session() as session:
        session.commit()
        afonte._pom_class_id = 'source' # need a set_mapper method
        # get a mapper that can generate a database entity from a group
        source_pom_mapper: PomSomMapper = PomSomMapper.get_pom_class(afonte._pom_class_id, session)
        # this converts a group to an database entity
        afonte_entity = source_pom_mapper.kgroup_to_entity(afonte, session)
        source_pom_mapper.store_KGroup(afonte, session)
        session.commit()
        source_orm = Entity.get_orm_for_pom_class(afonte._pom_class_id)
        same_fonte = session.get(source_orm,afonte.id.core)
        assert str(afonte.obs) == str(same_fonte.obs)
        session.close()







