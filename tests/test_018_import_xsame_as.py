"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""

# pylint: disable=import-error
from pathlib import Path
from typing import List
# import pdb

import pytest
from sqlalchemy import select

from tests import TEST_DIR, skip_on_travis
from timelink.api.models.relation import Relation
from timelink.api.models.system import KleioImportedFile
from timelink.kleio.kleio_server import KleioFile
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.rentity import Link
from timelink.api.database import (
    TimelinkDatabase
)

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis

db_path = Path(TEST_DIR, "sqlite")
TEST_DB = "xsameas"
# rentity_db = ":memory:"

# set a list of files to be imported before the tests begin
# relative to KLEIO_HOME
TEST_FILES_DIR = "projects/test-project/sources/reference_sources/rentities"

test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param

    database = TimelinkDatabase(
        db_name=db_name,
        db_type=db_type,
        db_path=db_path,
        kleio_server=kleio_server)

    try:
        yield database
    finally:
        database.session().close()
        database.drop_db()


@pytest.mark.parametrize(
    "dbsystem",
    test_set,
    indirect=True,
)
def test_import_xsameas(dbsystem: TimelinkDatabase):
    # Test that the sequence of import files does not affect the result
    file1 = f"{TEST_FILES_DIR}/sameas-tests.cli"
    file2 = f"{TEST_FILES_DIR}/xsameas-tests.cli"

    with dbsystem.session() as session:

        dbsystem.update_from_sources(file1)
        dbsystem.update_from_sources(file2)

        # check the number of KleioFiles imported
        stmt = select(KleioImportedFile)

        kfiles = session.execute(stmt).scalars().all()
        print(len(kfiles))

        # count the number of links
        stmt = select(Link)
        links = session.execute(stmt).scalars().all()
        linked_entities = sorted([link.entity for link in links])
        linked_rentities = sorted([link.rid for link in links])

        nlinks = len(links)

        # the problem here is that 'bio-michele-ruggieri-his4-19-per1-21'
        # occurs twice in the link list
        # ('rp744201',
        # 'bio-michele-ruggieri-his4-19-per1-21',
        # 'xsameas-tests')
        # this a bug in the sameas processing
        # count the number of relations with None in destination
        stmt = select(Relation).where(Relation.destination is None)
        relations = session.execute(stmt).scalars().all()
        nrelations = len(relations)

        # We now reimport file1 and check if the number of links and relations is the same
        importfile1: List[KleioFile] = dbsystem.kserver.get_translations(file1)
        xml_file = importfile1[0].xml_url
        import_from_xml(
            xml_file,
            session,
            options={
                "return_stats": True,
                "kleio_token": dbsystem.kserver.get_token(),
                "kleio_url": dbsystem.kserver.get_url(),
                "mode": "TL",
            },
        )

        stmt = select(Link)
        links2 = session.execute(stmt).scalars().all()
        linked_entities_2 = sorted([link.entity for link in links2])
        linked_rentities_2 = sorted([link.rid for link in links2])

        diff = set(linked_entities) - set(linked_entities_2)
        re_diff = set(linked_rentities) - set(linked_rentities_2)
        print(diff, re_diff)
        # this fails because the redundant link above was
        # removed in this phase.
        assert len(links) == nlinks, "wrong number of links"
        assert len(relations) == nrelations, "wrong number of relations"
        assert len(diff) == 0, "wrong number of occurrences linked"
        assert len(re_diff) == 0, "wrong number of rentities linked"

        stmt = select(Relation).where(Relation.destination == None)  # noqa
        relations2 = session.execute(stmt).scalars().all()
        assert len(relations2) == nrelations, "some relations have no destination after reimport"
