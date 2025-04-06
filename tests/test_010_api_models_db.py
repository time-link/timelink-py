import os
import warnings

import pytest  # pylint: disable=import-error
from sqlalchemy import select  # noqa

from tests import TEST_DIR, skip_on_travis
from timelink.kleio.groups import KElement, KGroup, KSource, KAct, KPerson, KGeoentity
from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # noqa
from timelink.api.models.base_class import Base
from timelink.api.models.entity import Entity  # noqa
from timelink.api.models.pom_som_mapper import PomSomMapper
from timelink.api.models.person import get_person
from timelink.api.models.source import Source

# pytestmark = skip_on_travis

db_path = f"{TEST_DIR}/sqlite/"
TEST_DB = "models"
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    # only used for sqlite databases

    database = TimelinkDatabase(db_name, db_type, db_path=db_path, echo=False)
    # attach a kleio server
    database.set_kleio_server(kleio_server)  # from tests.__init__.py
    try:

        yield database
    finally:
        database.session().close()
        database.drop_db()


@pytest.fixture
def kgroup_person_attr_rel() -> KSource:
    """Returns a group wtih attr and rel"""
    ks = KSource(
        "s2",
        type="test",
        loc="auc",
        ref="attr-rel",
        obs="""
        This is a multiline obs with special characteres like /,= and $
        """,
    )
    ka1 = KAct(
        "a2-1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="macau",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)

    kg = KGeoentity(id="geo1", name="my name is test-geo", type="geo-test-typ", obs="Test Geo")
    ka1.include(kg)

    p1 = KPerson("Joaquim", "m", "p01-2", obs="Living in Macau/China")
    # note attr with empty "obs"
    p1.attr("residencia", "Macau", date="2021-12-11", obs="")
    mobs = """
    Moving from Portugal
    to Macau in 2022
    """
    p2 = KPerson("Margarida", "f", "p02-2", obs=mobs)
    p2.attr("residencia", "Trouxemil", date="2020-10-18")
    p1.rel("parentesco", "marido", p2.name, p2.id, date="2006-01-4", obs="Ilha Terceira")
    ka1.include(p2)
    ka1.include(p1)
    return ks


@pytest.fixture
def kgroup_nested() -> KSource:
    """Returns a nested Kleio structure

    This is a nested Kleio Group Source/Act/Person/Attribute
    """
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    ka1 = KAct(
        "a1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)
    ka2 = KAct(
        "a2",
        "test-act",
        date="2021-07-17",
        day=17,
        month=7,
        year=2021,
        loc="auc",
        ref="p.2",
        obs="Test Act",
    )

    ks.include(ka2)
    p1 = KPerson("Joaquim", "m", "p01")
    p1.attr("residencia", ("Macau", "Em Chinês AoMen", "澳门"), date="2021-12-11")
    p2 = KPerson("Margarida", "f", "p02")
    p2.attr("residencia", "Trouxemil", date="2020-10-18")
    p3 = KPerson("Pedro", "m", "p03")
    p3.attr("residencia", "Coimbra", date="2021-10-21")

    ka1.include(p1)
    ka1.include(p2)
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
    assert os.getenv("TRAVIS") != "true"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_create_db(dbsystem):
    # Database is created and initialized in the fixture
    metadata = Base.metadata
    tables = list(metadata.tables.keys())
    assert len(tables) > 0, "tables where not created"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_create_eattribute(dbsystem, kgroup_nested):
    # Database is created and initialized in the fixture
    db: TimelinkDatabase = dbsystem
    ks = kgroup_nested
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()

    # views = inspect(db.get_engine()).get_view_names()
    # l1 = len(views)
    eattr = db._create_eattribute_view()
    # l2 = len(inspect(dbsystem.get_engine()).get_view_names())

    assert eattr is not None

    with dbsystem.session() as session:
        stmt = select(eattr).where(eattr.c.entity == "p01")
        results = session.execute(stmt).all()

    for result in results:
        print(result)


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_get_person(dbsystem, kgroup_nested):
    # Database is created and initialized in the fixture
    ks = kgroup_nested
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()

    with dbsystem.session() as session:
        p = get_person("p01", session=session)
        assert p is not None, "Person not found with get_person"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_create_pattribute(dbsystem, kgroup_nested):
    # Database is created and initialized in the fixture
    db: TimelinkDatabase = dbsystem
    ks = kgroup_nested
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()

    # views = inspect(db.get_engine()).get_view_names()
    # l1 = len(views)
    pattr = db.get_view("nattributes")
    # l2 = len(inspect(dbsystem.get_engine()).get_view_names())
    assert pattr is not None


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_create_nfucntions(dbsystem, kgroup_nested):
    # Database is created and initialized in the fixture
    db: TimelinkDatabase = dbsystem
    ks = kgroup_nested
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()

    # views = inspect(db.get_engine()).get_view_names()
    # l1 = len(views)
    nfunc = db._create_nfunction_view()
    # l2 = len(inspect(dbsystem.get_engine()).get_view_names())
    assert nfunc is not None


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_entity_contains(dbsystem):
    """Test entity contains relationship

    In this test four entities are created
    with one containing two others and one of the contained
    entities containing the fourth entity.

    Note that adding the top level entity
    to the session will add all entities to the session
    and deleting the top level entity will delete all entities.

    """
    ent1: Entity = Entity(id="e001", groupname="entity")
    ent1.pom_class = "entity"
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

    with dbsystem.session() as session:
        session.add(ent1)  # this adds the four entities to the database
        session.commit()
        ent4 = ent2.contained_by  # pylint: disable=no-member
        assert ent4 is ent1
        ent5 = ent1.contains[1]
        assert ent5 is ent3
        session.delete(ent1)  # should delete ent2, ent3 and ent4
        session.commit()
        deleted = session.get(Entity, "e004")
        assert deleted is None, "Should have deleted orphan"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_ensure_mapping(dbsystem):
    """Test that all classes registered in the classes table are mapped to ORM

    During database initialization, the classes and class_attributes tables
    is populated with definitions of base classes. Also in the timelink.api.models
    package, the base classes are defined as ORM classes. This test checks that
    all classes in the classes table are mapped to ORM classes.

    """
    with dbsystem.session() as session:
        pom_ids = PomSomMapper.get_pom_class_ids(session=session)
        pom_tables = []
        pom_class: PomSomMapper
        for pom_id in pom_ids:
            pom_class = PomSomMapper.get_pom_class(pom_id, session=session)

            # this is a hack to handle the fact that in the test suite
            # we connect to different databases that can, by import,
            # have different pom_class definition.
            if pom_class is not None:
                pom_class.ensure_mapping(session=session)
                pom_tables.append(pom_class.table_name)
                # print(repr(pom_class))
                # print(pom_class)
            else:
                warnings.warn(f"POM class with ID {pom_id} is not defined in the current database.",
                              stacklevel=2)
        orm_mapped_classes = Entity.get_som_mapper_to_orm_as_dict()
        non_mapped = set(pom_ids) - set(orm_mapped_classes.keys())
        assert len(non_mapped) == 0, "Not all classes are mapped to ORM"
        orm_mapped_tables = Entity.get_tables_to_orm_as_dict()
        tables_not_mapped = set(pom_tables) - set(orm_mapped_tables)
        assert len(tables_not_mapped) == 0, "Not all class tables are mapped in ORM"
        db_tables = dbsystem.db_table_names()
        tables_not_in_db = set(orm_mapped_tables) - set(db_tables)
        # it is possible that some tables are not in the database if they are associated
        # dynamic orm models not present in this database
        dynamic_tables = Entity.get_dynamic_orm_table_names()
        if len(tables_not_in_db) > 0:
            print(f"Tables not in db: {tables_not_in_db}")
            print(f"Dynamic tables: {dynamic_tables}")
            # remove dynamic tables from the list of tables not in db
            tables_not_in_db = tables_not_in_db - set(dynamic_tables)
            assert len(tables_not_in_db) == 0, "Not all mapped tables were created in the db"
        session.close()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_insert_nested_groups(dbsystem, kgroup_nested):
    """Test inserting a nested Kleio group"""
    ks = kgroup_nested
    source_id = ks.get_id()
    with dbsystem.session() as session:
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


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_insert_entities_attr_rel(dbsystem, kgroup_person_attr_rel):
    """Test inserting a group with attributes and relationships"""
    ks = kgroup_person_attr_rel
    source_id = ks.get_id()
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        source_from_db = Entity.get_entity(source_id, session)
        assert source_from_db.id == ks.get_id()
        # test if empty obs are removed from kleio rendering
        a_person = Entity.get_entity("p01-2", session)
        # the first attribute has an empty obs element should not be rendered
        kleio = a_person.attributes[0].to_kleio()
        assert "obs" not in kleio, "Empty obs should not be rendered"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_export_entities_as_kleio(dbsystem, kgroup_person_attr_rel):
    """Test exporting entities as Kleio"""
    ks = kgroup_person_attr_rel
    source_id = ks.get_id()
    with dbsystem.session() as session:
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        source_from_db = Entity.get_entity(source_id, session)
        ksource = source_from_db.to_kleio(ident_inc="...")
        assert ksource
        act = source_from_db.contains[0]
        kact = act.to_kleio()
        assert kact
        people = act.contains
        people_ids = [person.id for person in people]
        dbsystem.export_as_kleio(people_ids, "tests/test_kleio_export.txt")
        assert os.path.exists("tests/test_kleio_export.txt")
        # read the file
        with open("tests/test_kleio_export.txt", "r") as f:
            kleio = f.read()
            assert kleio
        os.remove("tests/test_kleio_export.txt")
        # special test for geoentities rendering
        geo = source_from_db.contains[0].contains[0]
        kgeo = geo.to_kleio()
        assert kgeo


def test_quote_and_long_test(kgroup_person_attr_rel):
    ks = kgroup_person_attr_rel
    kleio = ks.to_kleio()
    assert '"""' in kleio, "Bad handling of long text"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_insert_delete_previous_source(dbsystem, kgroup_nested):
    ks = kgroup_nested
    source_id = ks.get_id()
    with dbsystem.session() as session:
        print(
            f"""

        =================
        Inserting a nested group

        {ks.to_kleio()}
        """
        )
        PomSomMapper.store_KGroup(ks, session)
        session.commit()
        ks2 = KSource(
            "s1",
            type="test",
            loc="auc",
            ref="alumni",
            obs="Empty should delete previous one",
        )

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


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_store_KGroup_1(dbsystem):
    """Test storing a group with non core group"""
    kfonte: KGroup = KSource.extend(
        "fonte",
        position=["id", "data"],
        also=["tipo", "ano", "obs", "substitui"],
        synonyms=[
            ("tipo", "type"),
            ("ano", "year"),
            ("data", "date"),
            ("substitui", "replace"),
        ],
    )
    afonte = kfonte(
        "f001",
        data=KElement("data", "2021-12-02", element_class="date"),
        tipo=KElement("tipo", "teste", element_class="type"),
        obs="First group stored through ORM with non core group",
    )
    with dbsystem.session() as session:
        session.commit()
        # this converts a group to an database entity
        afonte_entity = PomSomMapper.kgroup_to_entity(afonte, session)
        assert afonte_entity is not None
        PomSomMapper.store_KGroup(afonte, session)
        session.commit()
        source_orm = Entity.get_orm_for_pom_class(afonte.pom_class_id)
        same_fonte = session.get(source_orm, afonte.id.core)
        assert str(afonte.obs) == str(same_fonte.obs)  # noqa
        assert str(afonte.data) == str(same_fonte.the_date)  # noqa
        session.close()
