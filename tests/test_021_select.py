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
    result = db.select("* FROM test_table")
    rows = result.fetchall()
    assert len(rows) == 2
    assert rows[0][1] == "Alice"
    assert rows[1][1] == "Bob"


def test_select_invalid_query(setup_database):
    """Test the select method with an invalid query."""
    db = setup_database
    with pytest.raises(sqlalchemy.exc.OperationalError):
        db.select("SELECT * FROM nonexistent_table")
