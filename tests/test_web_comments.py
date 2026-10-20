"""Test entity comments (timelink.web.models.activity.Comment)."""

# pylint: disable=import-error
from pathlib import Path

import pytest

from tests import TEST_DIR, skip_on_travis
from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.web.models.activity import ActivityBase, Comment

pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem(kleio_server):
    database = TimelinkDatabase(
        db_name="comments_test", db_type="sqlite",
        db_path=Path(TEST_DIR, "sqlite"), kleio_server=kleio_server,
    )
    ActivityBase.metadata.create_all(database.engine, tables=[Comment.__table__])
    try:
        yield database
    finally:
        database.session().close()
        database.drop_db()


def test_comment_roundtrip(dbsystem):
    with dbsystem.session() as session:
        session.query(Comment).filter(Comment.entity_id == "test-entity").delete()
        session.add(Comment(entity_id="test-entity", user_name="tester",
                            text="first comment"))
        session.add(Comment(entity_id="test-entity", user_name="other",
                            text="second comment"))
        session.commit()

        comments = (
            session.query(Comment)
            .filter(Comment.entity_id == "test-entity")
            .order_by(Comment.created)
            .all()
        )
        assert [c.text for c in comments] == ["first comment", "second comment"]
        assert comments[0].user_name == "tester"
