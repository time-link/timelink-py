"""Test the timelink.linking service layer used by the web linking UI."""

# pylint: disable=import-error
from pathlib import Path

import pytest

from tests import TEST_DIR, skip_on_travis
from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.models.rentity import REntity
from timelink.linking import service as linking

pytestmark = skip_on_travis

db_path = Path(TEST_DIR, "sqlite")
TEST_DB = "linking_service"
TEST_FILES_DIR = "projects/test-project/sources/reference_sources/rentities"


@pytest.fixture(scope="module")
def dbsystem(kleio_server):
    """Create a database and import the sameas test sources."""
    database = TimelinkDatabase(
        db_name=TEST_DB, db_type="sqlite", db_path=db_path, kleio_server=kleio_server
    )
    try:
        database.update_from_sources(
            Path(TEST_FILES_DIR, "sameas-tests.cli"), force=True
        )
        yield database
    finally:
        database.session().close()
        database.drop_db()


def _occurrences(dbsystem):
    with dbsystem.session() as session:
        return [
            id_
            for (id_,) in session.query(Person.id)
            .filter(Person.name.like("Mat%Ricci"))
            .all()
        ]


def test_same_as_and_get_rid(dbsystem):
    occurrences = _occurrences(dbsystem)
    assert len(occurrences) >= 4, "expected the sameas test persons"

    with dbsystem.session() as session:
        # clean slate for this test
        for rid in session.query(REntity.id).all():
            REntity.delete(rid[0], session=session)

        rentity = linking.same_as(occurrences[0], occurrences[1], "tester", session)
        assert rentity.id.startswith("rp")

        assert linking.get_rid_for(occurrences[0], "tester", session) == rentity.id
        assert linking.get_rid_for(occurrences[1], "tester", session) == rentity.id
        assert linking.get_rid_for(occurrences[0], "other", session) is None


def test_attach_to_existing_rid(dbsystem):
    occurrences = _occurrences(dbsystem)
    with dbsystem.session() as session:
        rid = linking.get_rid_for(occurrences[0], "tester", session)
        if rid is None:
            rid = linking.same_as(
                occurrences[0], occurrences[1], "tester", session
            ).id

        rentity = linking.same_as(occurrences[2], rid, "tester", session)
        assert rentity.id == rid

        attached = linking.rperson_occurrences(rid, session)
        assert {e.id for e in attached} >= {occurrences[0], occurrences[1], occurrences[2]}


def test_unlink(dbsystem):
    occurrences = _occurrences(dbsystem)
    with dbsystem.session() as session:
        rid = linking.get_rid_for(occurrences[0], "tester", session)
        if rid is None:
            rid = linking.same_as(
                occurrences[0], occurrences[1], "tester", session
            ).id
        # ensure all three occurrences are linked for this user
        for occ in occurrences[:3]:
            if linking.get_rid_for(occ, "tester", session) is None:
                linking.same_as(occ, rid, "tester", session)

        # unlink one occurrence: rid survives, occurrence is free
        unlinked = linking.unlink_occurrence(occurrences[0], "tester", session)
        assert unlinked == rid
        assert linking.get_rid_for(occurrences[0], "tester", session) is None
        assert session.get(REntity, rid) is not None

        # unlink the rest: rid disappears with its last link
        linking.unlink_occurrence(occurrences[1], "tester", session)
        linking.unlink_occurrence(occurrences[2], "tester", session)
        assert session.get(REntity, rid) is None

        # unlinking something unlinked is a no-op
        assert linking.unlink_occurrence(occurrences[0], "tester", session) is None
