import pytest

# Session is shared by all tests
from tests import Session
from tests import skip_on_travis, mhk_absent, conn_string
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.db import TimelinkDB
from timelink.mhk.models.entity import Entity  # noqa
from timelink.mhk.utilities import is_mhk_installed, get_connection_string


@pytest.fixture(scope="module")
def dbsystem_sqlite():  # this is the sqlite db
    db = TimelinkDB(conn_string)
    Session.configure(bind=db.get_engine())
    yield db
    with Session() as session:
        db.drop_db(session)


@pytest.fixture(scope="module")
def dbsystem_mhk():
    db_mhk = None
    if is_mhk_installed():
        mhk_conn_str = get_connection_string("MHK")
        db_mhk = TimelinkDB(mhk_conn_str)
    yield db_mhk


@skip_on_travis
@mhk_absent
def test_dual_metadata(dbsystem_sqlite, dbsystem_mhk):
    meta_sqlite = dbsystem_sqlite.get_metadata()
    meta_mhk = dbsystem_mhk.get_metadata()
    assert meta_mhk is not meta_sqlite
