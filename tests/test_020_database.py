"""Test tview creation, describe models and tables.
Check tests.__init__.py for parameters

"""

# pylint: disable=import-error
import logging

import pytest
from sqlalchemy import Engine, MetaData, select
from sqlalchemy.orm import aliased

from tests import TEST_DIR, skip_on_travis
from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.attribute import Attribute
from timelink.api.models.base import Person
from timelink.api.models.system import KleioImportedFile
from timelink.api.views import DropView, view, view_exists

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis
path_to_db_test_files = "projects/test-project/sources/database_tests"
db_path = f"{TEST_DIR}/sqlite/"
TEST_DB = "database_tests"
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    # only used for sqlite databases
    if db_type == "postgres":
        pass  # for debug
    database = TimelinkDatabase(
        db_name,
        db_type,
        db_path=db_path,
        kleio_server=kleio_server,
        drop_if_exists=True,
        echo=False,
    )
    # attach a kleio server
    database.update_from_sources(path_to_db_test_files, force=True)
    try:

        yield database
    finally:
        database.drop_db()
        database.session().close()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_create_and_drop_view(dbsystem: TimelinkDatabase):
    logging.basicConfig()
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    """ test the creation and dropping of views"""
    eng: Engine = dbsystem.engine
    metadata: MetaData = dbsystem.metadata
    person = Person.__table__
    attribute = Attribute.__table__

    views_before = dbsystem.view_names()
    print(views_before)

    view_name = "tview1"

    if view_name in views_before:
        stmt = DropView(view_name).execute_if(callable_=view_exists)

        with dbsystem.session() as session:
            session.execute(stmt)
            session.commit()

    test_view = view(
        view_name,
        metadata,
        select(
            person.c.id.label("id"),
            person.c.name.label("name"),
            person.c.sex.label("sex"),
            attribute.c.the_type.label("the_type"),
            attribute.c.the_value.label("the_value"),
            attribute.c.the_date.label("the_date"),
            person.c.obs.label("pobs"),
            attribute.c.obs.label("aobs"),
        ).select_from(person.join(attribute, person.c.id == attribute.c.entity)),
    )
    dbsystem.describe(test_view, show=True)
    views_after_def = dbsystem.view_names()
    print(views_after_def)
    assert view_name not in views_after_def

    metadata.create_all(eng)
    views_after_create = dbsystem.view_names()
    print(views_after_create)
    assert view_name in views_after_create

    stmt = DropView(view_name).execute_if(callable_=view_exists)

    with dbsystem.session() as session:
        session.execute(stmt)
        session.commit()

    views_after_delete = dbsystem.view_names()
    print(views_after_delete)
    assert view_name not in views_after_delete


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_get_nfunction_view(dbsystem):
    """Test the get_nfunction_view method."""

    # Get the nfunction view
    nfunc_view = dbsystem.get_view("nfunctions")
    assert nfunc_view is not None, "nfunction view should not be None"

    # Query the nfunction view
    with dbsystem.session() as session:
        stmt = select(nfunc_view).where(nfunc_view.c.func == "pad")
        results = session.execute(stmt).all()

    assert len(results) > 0, "There should be one result in the nfunction view"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_get_pairs_by_function(dbsystem):
    "Test de capacity to get pairs by function in the same act"
    nfunc = dbsystem.get_view("nfunctions")
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
def test_describe(dbsystem: TimelinkDatabase):
    "Test the describe method"

    nv = dbsystem.get_view("nfunctions")
    dbsystem.describe(nv, show=True)
    dbsystem.describe("act", show=True)
    dbsystem.describe(KleioImportedFile, show=True)
    dbsystem.describe(Person, show=True)
    pass


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_pperson_prints_kleio(dbsystem: TimelinkDatabase, capsys):
    """Test that pperson prints the Kleio representation of a person."""
    with dbsystem.session() as session:
        one_person = session.query(Person).first()
        dbsystem.pperson(one_person.id, session=session)
        captured = capsys.readouterr()
        assert len(captured.out) > 0
