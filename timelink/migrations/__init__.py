# This is a file for the "migrations" folder in timelink.
# It is used to hold the alembic related files and configurations.
# These allow for the update of databases when the models from within
# the timelink package without user intervention.
#
# this file and the techniques used are based on the following SO answer:
# https://stackoverflow.com/questions/73633063/distribute-alembic-migration-scripts-in-application-package
# This might be generating and error related to "formaters" in some cases.
# Check the following link for more information:
# https://stackoverflow.com/questions/47636747/python3-6-keyerror-formatters
# it might be related to the way we configure the path to the alembic.ini file.
from pathlib import Path

from alembic import command
from alembic.runtime import migration
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import engine


ROOT_PATH = Path(__file__).parent.parent
ALEMBIC_CFG = Config(ROOT_PATH / "alembic.ini")
ALEMBIC_CFG.set_main_option("script_location", str(ROOT_PATH / "migrations"))

# Naming conventions for foreign keys
# https://alembic.sqlalchemy.org/en/latest/naming.html#naming-conventions
naming_convention = {
    "fk":
    "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}


def set_db_url(db_url):
    """Set the database URL in the alembic configuration.

    This should be done before running any alembic commands in a specific database
    """
    ALEMBIC_CFG.set_section_option("alembic", "sqlalchemy.url", db_url)


# Unused
def get_versions(base='base', head='heads'):
    """Get the list of versions of the database.

    Args:
        base (str): The base revision to start from.
        head (str): The head revision to stop at.
    """
    script = ScriptDirectory.from_config(ALEMBIC_CFG)
    revisions = list(script.walk_revisions(base, head))
    return revisions


def current(db_url, verbose=False):
    """Get the current revision of the database."""
    set_db_url(db_url)
    command.current(ALEMBIC_CFG, verbose=verbose)


def upgrade(db_url, revision="heads"):
    """Upgrade the database to a given revision (default most recent)."""
    set_db_url(db_url)
    command.upgrade(ALEMBIC_CFG, revision)


def downgrade(db_url, revision):
    """Downgrade the database to the given revision."""
    set_db_url(db_url)
    command.downgrade(ALEMBIC_CFG, revision)


def heads(db_url):
    """ Show heads of database"""
    set_db_url(db_url)
    engine_ = engine.create_engine(db_url)
    with engine_.begin() as connection:
        migration_context = migration.MigrationContext.configure(connection)
        heads = migration_context.get_current_heads()
    return heads


def stamp(db_url, revision: str):
    """ Stamp current revision to a given revision
    Use "heads" to mark the database as up-to-date
    """
    set_db_url(db_url)
    command.stamp(ALEMBIC_CFG, revision)


def history(verbose=False):
    """Show the migration history."""
    command.history(ALEMBIC_CFG, verbose=verbose)


def autogenerate(db_url, message):
    """Autogenerate migration script."""
    set_db_url(db_url)
    command.revision(ALEMBIC_CFG, message=message, autogenerate=True)


def revision(db_url, message, autogenerate=False):
    """Create a new revision."""
    set_db_url(db_url)
    command.revision(ALEMBIC_CFG, message=message, autogenerate=autogenerate)
