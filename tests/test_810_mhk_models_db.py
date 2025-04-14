import os

# pylint: disable=import-error

import pytest

# Session is shared by all tests
from tests import Session
from tests import skip_on_travis, conn_string
from timelink.kleio.groups import KElement, KGroup, KSource, KAct, KPerson
from timelink.mhk.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.mhk.models.base_class import Base
from timelink.mhk.models.db import TimelinkMHK
from timelink.mhk.models.entity import Entity  # noqa
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.source import Source
from timelink.mhk.utilities import is_mhk_installed

pytestmark = skip_on_travis

if not is_mhk_installed():
    pytest.skip("skipping MHK tests (MHK not present)", allow_module_level=True)


@pytest.fixture(scope="module")
def dbsystem():
    db = TimelinkMHK(conn_string)
    Session.configure(bind=db.get_engine())
    yield db
    with Session() as session:
        db.drop_db(session)


@pytest.fixture
def kgroup_person_attr_rel() -> KSource:
    """Returns a group wtih attr and rel"""
    ks = KSource('s2', type='test', loc='auc', ref='attr-rel', obs="""
        This is a multiline obs with special characteres like /,= and $
        """)
    ka1 = KAct('a2-1', 'test-act', date='2021-07-16',
               day=16, month=7, year=2021,
               loc='macau', ref='p.1', obs='Test Act')
    ks.include(ka1)
    p1 = KPerson('Joaquim', 'm', 'p01-2', obs="Living in Macau/China")
    p1.attr('residencia', 'Macau', date='2021-12-11')
    mobs = """
    Moving from Portugal
    to Macau in 2022
    """
    p2 = KPerson('Margarida', 'f', 'p02-2', obs=mobs)
    p2.attr('residencia', 'Trouxemil', date='2020-10-18')
    p1.rel('parentesco', 'marido', p2.name, p2.id,  # pylint: disable=no-member
           date='2006-01-4', obs='Ilha Terceira')
    ka1.include(p2)
    ka1.include(p1)
    return ks


@pytest.fixture
def kgroup_nested() -> KSource:
    """Returns a nested structure"""
    ks = KSource('s1', type='test', loc='auc', ref='alumni', obs='Nested')
    ka1 = KAct('a1', 'test-act', date='2021-07-16',
               day=16, month=7, year=2021,
               loc='auc', ref='p.1', obs='Test Act')
    ks.include(ka1)
    ka2 = KAct('a2', 'test-act', date='2021-07-17',
               day=17, month=7, year=2021,
               loc='auc', ref='p.2', obs='Test Act')

    ks.include(ka2)
    p1 = KPerson('Joaquim', 'm', 'p01')
    p1.attr('residencia', 'Macau', date='2021-12-11')
    p2 = KPerson('Margarida', 'f', 'p02')
    p2.attr('residencia', 'Trouxemil', date='2020-10-18')
    p3 = KPerson('Pedro', 'm', 'p03')
    p3.attr("residencia", "Coimbra", date='2021-10-21')

    ka1.include(p3)
    p4 = KPerson("Maria", "f", "p04")
    p5 = KPerson("Manuel", "m", "p05")
    p6 = KPerson("João", "m", "p06")
    ka2.include(p4)
    ka2.include(p5)
    ka2.include(p6)
    return ks


@skip_on_travis
def test_succeed_if_not_in_travis():
    assert os.getenv("TRAVIS") != 'true'


def test_create_db(dbsystem):
    # Database is created and initialized in the fixture
    metadata = Base.metadata  # pylint: disable=no-member
    tables = list(metadata.tables.keys())
    assert len(tables) > 0, "tables where not created"


@skip_on_travis
def test_entity_contains(dbsystem):
    ent1: Entity = Entity(id='e001', groupname='entity')
    ent1.pom_class = 'entity'
    ent1.line = 1
    ent1.level = 1
    ent1.sequence = 1

    ent2: Entity = Entity(id="e002")
    ent2.groupname = "entity"
    ent2.pom_class = "entity"
    ent2.line = 2
    ent2.level = 2
    ent2.sequence = 2
    ent1.contains.append(ent2)

    ent3: Entity = Entity(id="e003")
    ent3.groupname = "entity"
    ent3.pom_class = "entity"
    ent3.line = 2
    ent3.level = 2
    ent3.sequence = 2
    ent1.contains.append(ent3)

    ent4: Entity = Entity(id="e004")
    ent4.groupname = "entity"
    ent4.pom_class = "entity"
    ent4.line = 4
    ent4.level = 4
    ent4.sequence = 4
    ent2.contains.append(ent4)

    with Session() as session:
        session.add(ent1)
        session.add(ent2)
        session.add(ent3)
        session.commit()
        ent4 = ent2.contained_by  # pylint: disable=no-member
        assert ent4 is ent1
        ent5 = ent1.contains[1]
        assert ent5 is ent3
        session.delete(ent1)  # should delete ent2, ent3 and ent4
        session.commit()
        deleted = session.get(Entity, "e004")
        assert deleted is None, "Should have deleted orphan"


def test_ensure_mapping(dbsystem):
    with Session() as session:
        pom_classes = PomSomMapper.get_pom_classes(session=session)
        pom_ids = PomSomMapper.get_pom_class_ids(session=session)
        pom_tables = [pom_class.table_name for pom_class in pom_classes]
        pom_class: PomSomMapper
        for pom_class in pom_classes:
            pom_class.ensure_mapping(session=session)
            # print(repr(pom_class))
            # print(pom_class)
        orm_mapped_classes = Entity.get_som_mapper_to_orm_as_dict()
        non_mapped = set(pom_ids) - set(orm_mapped_classes.keys())
        assert len(non_mapped) == 0, "Not all classes are mapped to ORM"
        orm_mapped_tables = Entity.get_tables_to_orm_as_dict()
        tables_not_mapped = set(pom_tables) - set(orm_mapped_tables)
        assert len(
            tables_not_mapped) == 0, "Not all class tables are mapped in ORM"
        db_tables = dbsystem.table_names()
        tables_not_in_db = set(orm_mapped_tables) - set(db_tables)
        assert len(
            tables_not_in_db) == 0, \
            "Not all mapped tables were created in the db"
        session.close()


def test_insert_entities_nested_groups(dbsystem, kgroup_nested):
    ks = kgroup_nested
    source_id = ks.get_id()
    with Session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        source_from_db: Source = Entity.get_entity(source_id, session)
        assert source_from_db.id == ks.get_id()
        assert repr(source_from_db)
        assert str(source_from_db)
        acts = source_from_db.contains
        act = acts[0]
        ract = repr(act)
        sact = str(act)
        assert ract
        assert sact
        person = act.contains[0]
        assert repr(person)
        assert str(person)


def test_insert_entities_attr_rel(dbsystem, kgroup_person_attr_rel):
    ks = kgroup_person_attr_rel
    source_id = ks.get_id()
    with Session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        source_from_db = Entity.get_entity(source_id, session)
        assert source_from_db.id == ks.get_id()


def test_quote_and_long_test(dbsystem, kgroup_person_attr_rel):
    ks = kgroup_person_attr_rel
    kleio = ks.to_kleio()
    assert '"""' in kleio, "Bad handling of long text"


def test_insert_delete_previous_source(dbsystem, kgroup_nested):
    ks = kgroup_nested
    source_id = ks.get_id()
    with Session() as session:
        print(
            f"""

        =================
        Inserting a nested group

        {ks.to_kleio()}
        """
        )
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        ks2 = KSource('s1', type='test',
                      loc='auc',
                      ref='alumni',
                      obs='Empty should delete previous one')

        print(
            """
        ================
        Reinserting group with same id
        ===============
        """
        )
        PomSomMapper.store_KGroup(ks2, session)
        source_from_db: Entity = Entity.get_entity(source_id, session)
        contains = source_from_db.contains
        assert len(contains) == 0, "import did not delete contained entities"


def test_store_KGroup_1(dbsystem):
    kfonte: KGroup = KGroup.extend('fonte',
                                   position=['id', 'data'],
                                   also=['tipo',
                                         'ano',
                                         'obs',
                                         'substitui'])
    afonte = kfonte('f001',
                    data=KElement('data', '2021-12-02', element_class='date'),
                    tipo=KElement('tipo', 'teste', element_class='type'),
                    obs="First group stored through ORM with non core group")
    with Session() as session:
        session.commit()
        afonte._pom_class_id = 'source'  # need a set_mapper method
        # this converts a group to an database entity
        afonte_entity = PomSomMapper.kgroup_to_entity(afonte, session)
        assert afonte_entity is not None
        PomSomMapper.store_KGroup(afonte, session)
        session.commit()
        source_orm = Entity.get_orm_for_pom_class(afonte.pom_class_id)
        same_fonte = session.get(source_orm, afonte.id.core)
        assert str(afonte.obs) == str(same_fonte.obs)  # pylint: disable=no-member
        session.close()
