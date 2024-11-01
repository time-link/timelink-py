# This is a file for the "migrations" folder in timelink.
# It is used to hold the alembic related files and configurations.
# These allow for the update of databases when the models from within
# the timelink package without user intervention.
#
# this file and the techniques used are based on the following SO answer:
# https://stackoverflow.com/questions/73633063/distribute-alembic-migration-scripts-in-application-package

from pathlib import Path

from alembic.config import Config
from alembic import command


ROOT_PATH = Path(__file__).parent.parent
ALEMBIC_CFG = Config(ROOT_PATH / "alembic.ini")
ALEMBIC_CFG.set_main_option("script_location", str(ROOT_PATH / "migrations"))


def set_db_url(db_url):
    """Set the database URL in the alembic configuration.

    This should be done before running any alembic commands in a specific database
    """
    ALEMBIC_CFG.set_section_option("alembic", "sqlalchemy.url", db_url)


def current(db_url, verbose=False):
    """Get the current revision of the database."""
    set_db_url(db_url)
    command.current(ALEMBIC_CFG, verbose=verbose)


def upgrade(db_url, revision="head"):
    """Upgrade the database to the given revision."""
    set_db_url(db_url)
    command.upgrade(ALEMBIC_CFG, revision)


def downgrade(db_url, revision):
    """Downgrade the database to the given revision."""
    set_db_url(db_url)
    command.downgrade(ALEMBIC_CFG, revision)