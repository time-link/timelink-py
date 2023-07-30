""" Test timelink Pandas integrations"""

import pytest
from pathlib import Path
from sqlalchemy.orm import sessionmaker

from timelink.api.database import TimelinkDatabase
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.database import TimelinkDatabase
from tests import skip_on_travis, TEST_DIR

from timelink.pandas import pname_to_df, attribute_values

pytestmark = skip_on_travis

@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    database = TimelinkDatabase(db_name, db_type, db_url, db_user, db_pwd)
    db = database.session()
    """Load sample data in the test database"""
    file: Path = Path(TEST_DIR, "xml_data/b1685.xml")
    try:
        import_from_xml(file, session=db)
    except Exception as exc:
        print(exc)
        raise
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
def test_name_to_df(dbsystem):
    """ test generation of dataframe with people with a certain name"""

    # test finding by similarity
    names_df = pname_to_df("matias carvalho", session=dbsystem, similar=True, sql_echo=True )
    print(names_df)
    assert names_df is not None, "name_to_df returned None"
    assert len(names_df) > 0

    # test finding by exact match
    names_df = pname_to_df("matias carvalho", sql_echo=True, session=dbsystem, similar=False)
    assert names_df is None, "name_to_df returned results but should not have"
    print(names_df)

@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "timelink", None, "postgres", "TCGllaFBFy"),
    ],
    indirect=True,
)    
def test_attribute_values(dbsystem):
    """ test generation of dataframe with people/objects with a certain attribute"""

    locais_residencia = attribute_values("residencia", session=dbsystem, sql_echo=True)
    assert locais_residencia is not None, "attribute_values returned None"
