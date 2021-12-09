import pytest
from sqlalchemy.orm import Session

from timelink.kleio.groups import KKleio, KSource, KAct, KAbstraction, KPerson, \
    KLs, KAtr, KGroup
from timelink.kleio.importer import import_from_xml
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.db import TimelinkDB
from timelink.mhk.models.entity import Entity
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base import Source, Person
from tests import Session, skip_on_travis

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis

conn_string = 'sqlite:///test_db?check_same_thread=False'



@pytest.fixture(scope="module")
def dbsystem():
    db = TimelinkDB(conn_string)
    Session.configure(bind=db.engine())
    yield db
    with Session() as session:
        db.drop_db(session)

@skip_on_travis
def test_import_xml(dbsystem):
    file = "xml_data/b1685.xml"
    with Session() as session:

        stats = import_from_xml(file, session, options={'return_stats': True})

        domingos_vargas = session.get(Person, 'b1685.33-per6')
        assert domingos_vargas is not None, "could not get a person from file"
        kleio = domingos_vargas.to_kleio()
        pass

@skip_on_travis
def test_import_with_custom_mapping(dbsystem):
    file = "xml_data/dev1692.xml"
    with Session() as session:
        stats = import_from_xml(file, session, options={'return_stats': True})

        caso = session.get(Entity, 'c1692-antonio-cordeiro-alcouc')
        caso_kleio = caso.to_kleio()
        assert caso is not None, "could not get an entity from special mapping"
        test = session.get(Entity, 'dev1692-per5')
        assert test is not None
        test_kleio = test.to_kleio()


@skip_on_travis
def test_import_with_many(dbsystem):
    file = "xml_data/test-auc-alunos-264605-A-140337-140771.xml"
    with Session() as session:
        stats = import_from_xml(file, session, options={'return_stats': True})
        estudante = session.get(Entity, '140771')
        kleio = estudante.to_kleio()
        assert estudante is not None, "could not get an entity from big import"
