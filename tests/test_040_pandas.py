"""Test timelink Pandas integrations"""

from pathlib import Path

import pytest
from sqlalchemy_utils import drop_database  # pylint: disable=unused-import. # noqa

from tests import TEST_DIR
from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.pandas import attribute_values, entities_with_attribute, pname_to_df

# import pdb  # noqa  TODO: remove when no longer needed


# pytestmark = skip_on_travis
TEST_DB = "test_pandas_db"
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]
test_files = "projects/test-project/sources/reference_sources/pandas"


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    db_path = Path(TEST_DIR, "sqlite")

    database = TimelinkDatabase(
        db_name, db_type, db_path=db_path, kleio_server=kleio_server, echo=False
    )
    database.update_from_sources(test_files)

    try:
        yield database
    finally:
        with database.session() as session:
            pass
            database.drop_db(session=session)
            session.close()
        if ":memory:" not in database.db_url:
            pass
            # drop_database(database.db_url)


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
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


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_attribute_values(dbsystem):
    """test generation of dataframe with people/objects with a certain attribute"""

    locais_residencia = attribute_values("residencia", db=dbsystem, sql_echo=True)
    assert locais_residencia is not None, "attribute_values returned None"
    attr_values = attribute_values("nacionalidade", db=dbsystem, sql_echo=True)
    assert attr_values is not None, "attribute_values returned None"
    # get count of unique values for Portugal
    attr_type_count = attr_values.loc["Portugal"]["count"]
    # now count filtering by groupname "n" (this filters out "referidos"
    attr_values_2 = attribute_values(
        "nacionalidade", groupname="n", db=dbsystem, sql_echo=True
    )
    # get count of unique values for Portugal
    attr_type_count_2 = attr_values_2.loc["Portugal"]["count"]
    assert attr_type_count > attr_type_count_2, "attribute_values returned bad results"


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_entities_with_attribute(dbsystem):
    """Test generation of dataframe from attributes"""
    df = entities_with_attribute(
        db=dbsystem,
        entity_type="person",
        the_type="jesuita-entrada",
        the_value=["Coimbra", "Goa, Índia"],
        show_elements=["name", "sex", "extra_info"],
        more_attributes=["jesuita-votos-local"],
        sql_echo=True,
    )
    assert df is not None, "entities_with_attribute returned None"
    assert len(df) > 0, "entities_with_attribute returned empty dataframe"
    print(df)


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_entities_with_attribute_filter_by(dbsystem):
    """Test generation of dataframe from attributes"""
    conimbricensis = [
        "deh-afonso-aires",
        "deh-antonio-de-abreu-ref1",
        "deh-antonio-de-andrade",
        "deh-goncalo-alvares",
        "deh-miguel-do-amaral",
        "deh-pedro-de-alcacova",
    ]
    df = entities_with_attribute(
        entity_type="person",
        show_elements=["name", "groupname"],
        the_type="jesuita-entrada",
        more_attributes=["nacionalidade", "nascimento"],
        filter_by=conimbricensis,
        sql_echo=True,
        db=dbsystem,
    )
    assert df is not None, "entities_with_attribute returned None"
    assert len(df.index.unique()) == len(
        conimbricensis
    ), "entities_with_attribute returned bad filtered dataframe"
    print(df)


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_entities_with_attribute_list(dbsystem):
    """Test generation of dataframe from attributes"""
    df = entities_with_attribute(
        db=dbsystem,
        entity_type="person",
        the_type=[
            "nascimento",
            "entrada",
            "partida",
            "estadia",
            "morte",
            "jesuita-entrada",
            "jesuita-votos-local",
        ],
        column_name="lugares",
        show_elements=["name", "sex", "the_line", "groupname"],
        more_attributes=[],
        filter_by=["deh-ludovico-antonio-adorno"],
        sql_echo=True,
    )
    # pdb.set_trace()
    assert df is not None, "entities_with_attribute_list returned None"
    assert len(df) > 0, "entities_with_attribute_list returned empty dataframe"
    df_cols = list(df.columns)
    required_column = "lugares.original"
    assert required_column in df_cols, f"{required_column} expected in {df_cols}"
    required_column = "lugares.comment"
    assert required_column in df_cols, f"{required_column} expected in {df_cols}"
    required_column = "lugares.line"
    assert required_column in df_cols, f"{required_column} expected in {df_cols}"
    # loop through the dataframe and check that column "groupname" is different from "a_groupname"
    for _index, row in df.iterrows():
        assert (
            row["groupname"] != row["lugares.groupname"]
        ), "groupname and [column_name].groupname should be different"
    print(df.info())


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_entities_with_attribute_empty(dbsystem):
    """Test generation of dataframe from attributes"""
    df = entities_with_attribute(
        db=dbsystem,
        entity_type="person",
        the_type="nonexistent",
        column_name="lugares",
        show_elements=["name", "sex", "the_line"],
        more_attributes=[],
        filter_by=["deh-ludovico-antonio-adorno"],
        sql_echo=True,
    )
    assert df is None, "entities_with_attribute failed to return None"

    df = entities_with_attribute(
        db=dbsystem,
        entity_type="person",
        the_type="nascimento",
        column_name="lugares",
        show_elements=["name", "sex", "the_line"],
        more_attributes=["nonexistent"],
        filter_by=["deh-ludovico-antonio-adorno"],
        sql_echo=True,
    )
    assert df is not None, "entities_with_attribute returned None"
