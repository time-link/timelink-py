""" Test timelink Pandas integrations"""

import pytest
from pathlib import Path
import pdb  # noqa  TODO: remove when no longer needed

from sqlalchemy_utils import drop_database  # pylint: disable=unused-import. # noqa

from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from tests import TEST_DIR

from timelink.api.models.person import Person
from timelink.kleio.groups.kelement import KType, KValue
from timelink.kleio.groups.kls import KLs

# pytestmark = skip_on_travis

TEST_DB = "elname"
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    db_path = Path(TEST_DIR, "sqlite")

    database = TimelinkDatabase(db_name, db_type, db_path=db_path, echo=False,
                                kleio_server=kleio_server)

    try:
        yield database
    finally:
        database.drop_db()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_element_name_bug(dbsystem):
    """Test element name bug"""
    database = dbsystem

    database.update_from_sources("projects/test-project/sources/reference_sources/issues/element_name", force=True)
    with dbsystem.session() as session:
        id = "el-antonio-de-abreu"
        ent = session.query(Person).filter(Person.id == id).one()
        for al in ent.attributes:
            print(al.to_kleio(), al.extra_info)
        attr_name_list = ent.attributes[0].get_element_names()
        print(attr_name_list)


    KTipo = KType.extend('tipo')  # noqa
    KValor = KValue.extend('valor')   # noqa
    ls = KLs.extend("ls", position=["tipo", "valor", "date"], also=["obs", "entity"])
    _als = ls("my type", "my value", "2023-01-01")
    print(_als)
    database.update_from_sources("sources/reference_sources/issues/element_name", force=True)

    with dbsystem.session() as session:
        id = "el-antonio-de-abreu"
        ent2 = session.query(Person).filter(Person.id == id).one()
        for al in ent2.attributes:
            print(al.to_kleio(), al.extra_info)
        attr2_name_list = ent.attributes[0].get_element_names()

    assert attr_name_list == attr2_name_list
