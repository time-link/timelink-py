"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""
# pylint: disable=import-error
import pytest
from sqlalchemy import select
from sqlalchemy.orm import aliased
from tests import TEST_DIR, skip_on_travis
from timelink.api.models.system import KleioImportedFile
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.database import (
    TimelinkDatabase,
)
from timelink.kleio import KleioServer

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis
path_to_db_test_files = "sources/database_tests"
db_path = f"{TEST_DIR}/sqlite/"
test_set = [("sqlite", "test_db"), ("postgres", "test_db")]


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name = request.param
    # only used for sqlite databases

    database = TimelinkDatabase(db_name, db_type, db_path=db_path)
    # attach a kleio server
    kleio_server = KleioServer.start(
        kleio_home=f"{TEST_DIR}/timelink-home/projects/test-project"
    )
    database.set_kleio_server(kleio_server)
    database.update_from_sources(path_to_db_test_files)
    try:

        yield database
    finally:
        # database.drop_db()
        database.session().close()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_get_nfunction_view(dbsystem):
    """Test the get_nfunction_view method."""

    # Get the nfunction view
    nfunc_view = dbsystem.nfunctions_view
    assert nfunc_view is not None, "nfunction view should not be None"

    # Query the nfunction view
    with dbsystem.session() as session:
        stmt = select(nfunc_view).where(nfunc_view.c.func == "pad")
        results = session.execute(stmt).all()

    assert len(results) > 0, "There should be one result in the nfunction view"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_get_pairs_by_function(dbsystem):
    "Test de capacity to get pairs by function in the same act"
    nfunc = dbsystem.nfunctions_view
    dbsystem.describe(nfunc, show=True)
    nfunc2 = aliased(nfunc)
    func1 = "senhorio"
    func2 = "enfiteuta"

    stmt = (
        select(
            nfunc.c.id_act,
            nfunc.c.act_type,
            nfunc.c.act_date,
            nfunc.c.id.label("id1"),
            nfunc.c.func.label("func1"),
            nfunc.c.name.label("name1"),
            nfunc2.c.id.label("id2"),
            nfunc2.c.func.label("func2"),
            nfunc2.c.name.label("name2"),
        )
        .join(nfunc2, onclause=(nfunc.c.id_act == nfunc2.c.id_act))
        .where(nfunc.c.func == func1)
        .where(nfunc2.c.func == func2)
    )
    print(stmt)
    with dbsystem.session() as session:
        results = session.execute(stmt).all()
        for r in results:
            print(r)
    assert len(results) > 0, "There should be one result in the nfunction view"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_describe(dbsystem):
    "Test the describe method"

    nv = dbsystem.nfunctions_view
    dbsystem.describe(nv, show=True)
    dbsystem.describe("act", show=True)
    dbsystem.describe(KleioImportedFile, show=True)
    dbsystem.describe(Person, show=True)
    pass
