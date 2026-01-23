import pytest
import sqlalchemy
from sqlalchemy import text
from timelink.api.database import TimelinkDatabase
from tests import TEST_DIR

db_path = f"{TEST_DIR}/sqlite/"
TEST_DB = "select_db"


@pytest.fixture
def setup_database():
    """Fixture to set up a test database."""
    db = TimelinkDatabase(db_type="sqlite", db_name=TEST_DB, db_path=db_path)
    with db.session() as session:
        session.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)"))
        session.execute(text("INSERT INTO test_table (id, name) VALUES (1, 'Alice')"))
        session.execute(text("INSERT INTO test_table (id, name) VALUES (2, 'Bob')"))
        session.commit()
    yield db
    db.drop_db()


def test_select_valid_query(setup_database):
    """Test the select method with a valid query."""
    db = setup_database
    rows = db.select("* FROM test_table")
    # When session is None, select() returns a list of rows directly
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[1][1] == "Bob"


def test_select_invalid_query(setup_database):
    """Test the select method with an invalid query."""
    db = setup_database
    with pytest.raises(sqlalchemy.exc.OperationalError):
        db.select("SELECT * FROM nonexistent_table")


def test_select_as_dataframe_no_session(setup_database):
    """Test the select method with as_dataframe=True and no session provided."""
    db = setup_database
    df = db.select("* FROM test_table", as_dataframe=True)
    assert df is not None
    assert len(df) == 2
    assert df.iloc[0]['name'] == "Alice"
    assert df.iloc[1]['name'] == "Bob"


def test_select_as_dataframe_with_session(setup_database):
    """Test the select method with as_dataframe=True and a provided session."""
    db = setup_database
    with db.session() as session:
        df = db.select("* FROM test_table", session=session, as_dataframe=True)
        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]['name'] == "Alice"
        assert df.iloc[1]['name'] == "Bob"


def test_select_with_session(setup_database):
    """Test the select method with an explicit session and as_dataframe=False."""
    db = setup_database
    with db.session() as session:
        result = db.select("* FROM test_table", session=session)
        # When session is provided and as_dataframe=False, returns a Result object
        rows = result.fetchall()
        assert len(rows) == 2
        assert rows[0][1] == "Alice"
        assert rows[1][1] == "Bob"
