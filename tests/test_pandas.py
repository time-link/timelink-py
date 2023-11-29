""" Test timelink Pandas integrations"""

import pytest
from pathlib import Path

from timelink.api.database import (
    TimelinkDatabase,
    is_postgres_running,
    get_postgres_container_user,
    get_postgres_container_pwd,
)
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from tests import skip_on_travis, TEST_DIR

from timelink.pandas import pname_to_df, attribute_to_df, attribute_values

pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    if db_type == "postgres" and is_postgres_running():
        db_user = get_postgres_container_user()
        db_pwd = get_postgres_container_pwd()
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
        yield database
    finally:
        database.drop_db(db)
        db.close()


@skip_on_travis
@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_name_to_df(dbsystem):
    """test generation of dataframe with people with a certain name"""

    # test finding by similarity
    names_df = pname_to_df("matias carvalho", db=dbsystem, similar=True, sql_echo=True)
    print(names_df)
    assert names_df is not None, "name_to_df returned None"
    assert len(names_df) > 0

    # test finding by exact match
    names_df = pname_to_df("matias carvalho", sql_echo=True, db=dbsystem, similar=False)
    assert names_df is None, "name_to_df returned results but should not have"
    print(names_df)


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_attribute_values(dbsystem):
    """test generation of dataframe with people/objects with a certain attribute"""

    locais_residencia = attribute_values("residencia", db=dbsystem, sql_echo=True)
    assert locais_residencia is not None, "attribute_values returned None"


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_attributes_to_df(dbsystem):
    """Test generation of dataframe from attributes"""
    df = attribute_to_df(
        db=dbsystem,
        the_type="residencia",
        the_value="soure",
        person_info=True,
        more_cols=[],
        sql_echo=True,
    )
    assert df is not None, "attribute_to_df returned None"
    assert len(df) > 0, "attribute_to_df returned empty dataframe"
    print(df)
