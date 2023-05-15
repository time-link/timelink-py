"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""
# pylint: disable=import-error

from pathlib import Path

import pytest

from tests import Session, skip_on_travis, TEST_DIR, conn_string
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.database import TimelinkDatabase
from timelink.api.models.entity import Entity

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    database = TimelinkDatabase(db_name, db_type, db_url, db_user, db_pwd)
    db = database.session()
    try:
        yield db
    finally:
        database.drop_db(db)
        db.close()


@skip_on_travis
@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "timelink", None, "postgres", "TCGllaFBFy"),
    ],
    indirect=True,
)
def test_import_xml(dbsystem):
    file: Path = Path(TEST_DIR, "xml_data/b1685.xml")
    session = dbsystem
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    domingos_vargas = session.get(Person, "b1685.33-per6")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0


@skip_on_travis
@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "timelink", None, "postgres", "TCGllaFBFy"),
    ],
    indirect=True,
)
def test_import_with_custom_mapping(dbsystem):
    file = Path(TEST_DIR, "xml_data/dev1692.xml")
    session = dbsystem
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile = stats["file"]
    assert "dev1692" in sfile.name
    caso = session.get(Entity, "c1692-antonio-cordeiro-alcouc")
    caso_kleio = caso.to_kleio()
    assert len(caso_kleio) > 0
    assert caso is not None, "could not get an entity from special mapping"
    caso_kleio = caso.to_kleio()
    assert len(caso_kleio) > 0
    test = session.get(Entity, "dev1692-per5")
    assert test is not None
    test_kleio = test.to_kleio()
    assert len(test_kleio) > 0


@skip_on_travis
@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "timelink", None, "postgres", "TCGllaFBFy"),
    ],
    indirect=True,
)
def test_import_with_many(dbsystem):
    file = Path(TEST_DIR, "xml_data/test-auc-alunos-264605-A-140337-140771.xml")
    session = dbsystem
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile = stats["file"]
    assert "alunos" in sfile.name
    estudante = session.get(Entity, "140771")
    kleio = estudante.to_kleio()
    assert len(kleio) > 0
    assert estudante is not None, (
        "could not get an entity from big import" @ skip_on_travis
    )  # noqa


@skip_on_travis
@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "timelink", None, "postgres", "TCGllaFBFy"),
    ],
    indirect=True,
)
def test_import_git_hub(dbsystem):
    file = "https://raw.githubusercontent.com/time-link/timelink-py/f76007cb7b98b39b22be8b70b3b2a62e7ae0c12f/tests/xml_data/b1685.xml"  # noqa
    session = dbsystem
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    domingos_vargas = session.get(Person, "b1685.33-per6")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0
    sfile: Path = stats["file"]
    assert "b1685.xml" in sfile
    pass
