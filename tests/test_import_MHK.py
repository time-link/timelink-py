# pylint: disable=import-error
from pathlib import Path

import pytest
from sqlalchemy.orm.session import Session

from tests import skip_on_travis, mhk_absent, conn_string, TEST_DIR
from timelink.kleio.importer import import_from_xml
from timelink.mhk.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.mhk.models.base import Person  # noqa pylint: disable=unused-import
from timelink.mhk.models.db import TimelinkMHK
from timelink.mhk.models.entity import Entity
from timelink.mhk.utilities import is_mhk_installed

# https://docs.pytest.org/en/latest/how-to/skipping.html

if not is_mhk_installed():
    pytest.skip("skipping MHK tests (MHK not present)", allow_module_level=True)

pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem():
    database = TimelinkMHK(conn_string)
    db = database.session()
    try:
        yield db
    finally:
        database.drop_db(db)
        db.close()


@skip_on_travis
@mhk_absent
def test_import_xml(dbsystem: Session):
    file: Path = Path(TEST_DIR, "xml_data/b1685.xml")
    session = dbsystem
    stats = import_from_xml(
        file, session, options={"return_stats": True, "mode": "MHK"}
    )
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    domingos_vargas = session.get(Person, "b1685.33-per6")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0


@skip_on_travis
@mhk_absent
def test_import_with_custom_mapping(dbsystem: Session):
    file = Path(TEST_DIR, "xml_data/dev1692.xml")
    session = dbsystem

    stats = import_from_xml(
        file, session, options={"return_stats": True, "mode": "MHK"}
    )
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
@mhk_absent
def test_import_with_many(dbsystem: Session):
    file = Path(TEST_DIR, "xml_data/test-auc-alunos-264605-A-140337-140771.xml")
    session = dbsystem
    stats = import_from_xml(
        file, session, options={"return_stats": True, "mode": "MHK"}
    )
    sfile = stats["file"]
    assert "alunos" in sfile.name
    estudante = session.get(Entity, "140771")
    kleio = estudante.to_kleio()
    assert len(kleio) > 0
    assert estudante is not None, (
        "could not get an entity from big import" @ skip_on_travis
    )  # noqa


@skip_on_travis
@mhk_absent
def test_import_git_hub(dbsystem: Session):
    file = "https://raw.githubusercontent.com/time-link/timelink-py/f76007cb7b98b39b22be8b70b3b2a62e7ae0c12f/tests/xml_data/b1685.xml"  # noqa
    session = dbsystem
    stats = import_from_xml(
        file, session, options={"return_stats": True, "mode": "MHK"}
    )

    domingos_vargas = session.get(Person, "b1685.33-per6")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0
    sfile: Path = stats["file"]
    assert "b1685.xml" in sfile
    pass
