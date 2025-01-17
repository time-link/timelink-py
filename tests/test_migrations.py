import random
import pytest
import tempfile

# Import the methods from __init__.py
from timelink.migrations import set_db_url, current, upgrade, downgrade
from timelink.migrations import ALEMBIC_CFG
from timelink.cli import parse_db_url, create_db_index
from timelink.api.database import TimelinkDatabase
from tests import reference_db_con_str, skip_on_travis


# Skip tests if running on Travis CI
pytestmark = skip_on_travis


@pytest.fixture
def timelink_db():
    temp_dir = tempfile.TemporaryDirectory()
    db_url = f"sqlite:///{temp_dir.name}/test.db"

    db = TimelinkDatabase(db_url=db_url)
    yield db


def test_create_reference_db():
    db: TimelinkDatabase = TimelinkDatabase(db_url=reference_db_con_str)
    print(db.table_names())
    result = upgrade(reference_db_con_str, revision="head")
    # Add assertions to check the database state if needed
    assert result is None


def test_set_db_url(timelink_db):
    db_url = timelink_db.db_url
    set_db_url(db_url)
    assert ALEMBIC_CFG.get_main_option("sqlalchemy.url") == db_url


def test_current(timelink_db):
    db_url = timelink_db.db_url
    set_db_url(db_url)
    current(db_url, verbose=True)
    # Add assertions to check the output if needed


def test_upgrade(timelink_db):
    db_url = timelink_db.db_url
    set_db_url(db_url)
    upgrade(db_url, revision="head")
    # Add assertions to check the database state if needed


def test_upgrade_random():
    # get list of databases avoiding _users table
    db_list = create_db_index(avoid_patterns=["_users"])
    for _ in range(5):   # try 5 random databases some are not upgradable
        db_key = list(db_list.keys())[random.randint(0, len(db_list) - 1)]
        db_url = parse_db_url(db_key)
        db: TimelinkDatabase = TimelinkDatabase(db_url=db_url)
        print(db.table_names())
        result = upgrade(db_url, revision="head")
        if result is None:
            break
        else:
            print(f"Failed to upgrade {db_url} {result}")
    # Add assertions to check the database state if needed
    assert result is None


def test_downgrade(timelink_db):
    db_url = timelink_db.db_url
    set_db_url(db_url)
    result = downgrade(db_url, revision="48dd")
    # Add assertions to check the database state if needed
    assert result is None
