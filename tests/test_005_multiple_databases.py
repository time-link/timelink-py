"""
This module contains tests for handling multiple databases using the TimelinkDatabase class.

SQLAlchemy associates ORM model with a Metadata object.

The Metadata object contains the "mappings", the correspondence
between ORM models and the database tables.

This mapping is made at load time of the Timelink package, because
it is created in the definition of timelink.api.models.base_class

But the mappings can be extended dynamically during import, when the kleio import file
includes new class definitions.

In those cases timelink generates a new ORM model dynamically and fills the tables "classes"
and "classes_attributes" with the information about the new mapping.

When the database with the dynamic mappings is openned later, timelink examines the
content of the class and class_attribute tables and recreates the dynamic ORM models
from them. This is done in PomSomMapper.ensure_mapping(session) method.

In an application that connects to different databases this poses a problem.
The application can open first a Database in which dynamic mappings exist and
recreate the ORM models according to the content of the class table.

Then, the same application will attach to a different database and checks if all the metadata
tables exist. If not it will create the missing tables, poluting the second database.

"""

import pytest  # pylint: disable=import-error
from tests import TEST_DIR
from timelink.api.database import TimelinkDatabase

# pytestmark = skip_on_travis

db_path = f"{TEST_DIR}/sqlite/"
TEST_DB = "mdb"


# The first time a database is created only the base tables are created
# The second time the same database is accessed the dynamic tables should be there
# this first time the second database is acessed the dynamic tables should not be there
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def test_setup(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    # only used for sqlite databases

    return db_type, db_name, kleio_server


@pytest.mark.parametrize("test_setup", test_set, indirect=True)
def test_multiple_databases(test_setup):
    """Test multiple databases"""
    db_type, db_name, kleio_server = test_setup

    database: TimelinkDatabase = TimelinkDatabase(
        db_name, db_type, db_path=db_path, kleio_server=kleio_server, drop_if_exists=True, echo=True
    )

    # count tables at creation
    tables_1 = database.metadata.sorted_tables
    assert len(tables_1) > 0, "no tables exist in metadata"
    ntables_1 = len(database.db_table_names())  # clean database tables

    # import source with dynamic mappings
    database.update_from_sources("projects/test-project/sources/reference_sources/issues/multiple_databases")
    # check tables in metadata after import, should be more than before
    tables_after_import = database.metadata.sorted_tables
    ntables_after_import = len(database.db_table_names())
    new_tables = set(tables_after_import) - set(tables_1)
    print(f"New tables: {new_tables}")
    # check if the tables were created
    assert ntables_after_import > ntables_1, "no dynamic tables created"

    # check if the dynamic mappings are there if reopenning the database
    database_again = TimelinkDatabase(
        db_name, db_type, db_path=db_path, kleio_server=kleio_server, echo=True
    )
    # check if the dynamic mappings are there
    ntables_after_reopening = len(database_again.db_table_names())
    assert ntables_after_reopening == ntables_after_import, "dynamic tables lost after reopening"

    database.drop_db()
    db_name2 = db_name + "2"
    # create a second database
    # note that the metadata object is shared because it is a global sqlalchemy
    # object. So the metadata object is the same for all instances of TimelinkDatabase
    database2 = TimelinkDatabase(db_name2, db_type, db_path=db_path, drop_if_exists=True, echo=True)
    tables_2 = database2.metadata.sorted_tables
    missing_tables = set(tables_after_import) - set(tables_2)
    print(f"Missing tables in new database, should be non empty: {missing_tables}")
    # count tables at creation
    ntables_2 = len(database2.db_table_names())
    # check if the tables are the same
    assert ntables_1 == ntables_2, "only base tables created in second database"
    database2.drop_db()
