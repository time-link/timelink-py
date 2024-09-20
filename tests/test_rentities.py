"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""
# pylint: disable=import-error
import logging
import os
from pathlib import Path
from time import sleep

import pytest

from tests import TEST_DIR, get_one_translation, skip_on_travis
from timelink.api.models.system import KleioImportedFile
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person, PomSomMapper
from timelink.api.models.rentity import REntity
from timelink.api.database import (
    TimelinkDatabase,
    start_postgres_server,
    get_postgres_container_user,
    get_postgres_container_pwd,
    get_import_status,
)
from timelink.api.models.entity import Entity

from timelink.kleio import KleioServer
from timelink.kleio.schemas import KleioFile

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    if db_type == "postgres":
        start_postgres_server()
        db_user = get_postgres_container_user()
        db_pwd = get_postgres_container_pwd()

    database = TimelinkDatabase(db_name, db_type, db_url, db_user, db_pwd)
    try:
        yield database
    finally:
        # database.drop_db
        database.session().close()


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        # change to pytest.param("postgres", "tests", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_xml(dbsystem):
    """Test the import of a Kleio file into the Timelink database"""
    file: Path = Path(TEST_DIR, "xml_data/sameas-tests.xml")
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile: Path = stats["file"]
        assert sfile.name == file.name
        ricci = session.get(Person, "sa-deh-matteo-ricci")
        assert ricci is not None, "could not get a person from file"
        kleio = ricci.to_kleio()
        occurences = [id for (id,)
                      in session.query(Person.id)
                      .filter(Person.name.like('Mat%Ricci')).all()
                      ]
        first = occurences[0]
        for occ in occurences[1:]:
            REntity.same_as(first, occ, session=session)
        assert len(kleio) > 0


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        # change to pytest.param("postgres", "tests", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_random_id(dbsystem):
    """Test the generation of a random id"""
    with dbsystem.session() as session:
        id1 = REntity.generate_id(session=session)
        id2 = REntity.generate_id(session=session)
        assert id1 != id2
