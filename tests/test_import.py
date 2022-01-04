from pathlib import Path

import pytest

from timelink.kleio.importer import import_from_xml
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.db import TimelinkDB
from timelink.mhk.models.entity import Entity
from timelink.mhk.models.base import Person
from tests import Session, skip_on_travis, TEST_DIR, conn_string

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem():
    db = TimelinkDB(conn_string)
    Session.configure(bind=db.engine())
    yield db
    with Session() as session:
        db.drop_db(session)


@skip_on_travis
def test_import_xml(dbsystem):
    file = Path(TEST_DIR, "xml_data/b1685.xml")
    with Session() as session:
        stats = import_from_xml(file, session, options={"return_stats": True})
        print()
        print(stats)
        domingos_vargas = session.get(Person, "b1685.33-per6")
        assert domingos_vargas is not None, "could not get a person from file"
        kleio = domingos_vargas.to_kleio()
        assert len(kleio) > 0


@skip_on_travis
def test_import_with_custom_mapping(dbsystem):
    file = Path(TEST_DIR, "xml_data/dev1692.xml")
    with Session() as session:
        stats = import_from_xml(file, session, options={"return_stats": True})
        print()
        print(stats)
        caso = session.get(Entity, "c1692-antonio-cordeiro-alcouc")
        assert caso is not None, "could not get an entity from special mapping"
        caso_kleio = caso.to_kleio()
        assert len(caso_kleio) > 0
        test = session.get(Entity, "dev1692-per5")
        assert test is not None
        test_kleio = test.to_kleio()
        assert len(test_kleio) > 0


@skip_on_travis
def test_import_many(dbsystem):
    file = Path(TEST_DIR, "xml_data/test-auc-alunos-264605-A-140337-140771.xml")
    with Session() as session:
        stats = import_from_xml(file, session, options={"return_stats": True})
        print()
        print(stats)
        estudante = session.get(Entity, "140771")
        kleio = estudante.to_kleio()
        assert estudante is not None, "could not get an entity from big import"
        assert len(kleio) > 0, "no kleio representation"


@skip_on_travis
def test_import_git_hub(dbsystem):
    file = "https://raw.githubusercontent.com/time-link/timelink-py/f76007cb7b98b39b22be8b70b3b2a62e7ae0c12f/tests/xml_data/b1685.xml"  # noqa: E501
    with Session() as session:
        stats = import_from_xml(file, session, options={"return_stats": True})
        print(stats)
        domingos_vargas = session.get(Person, "b1685.33-per6")
        assert domingos_vargas is not None, "could not get a person from file"
        kleio = domingos_vargas.to_kleio()
        assert len(kleio) > 0
