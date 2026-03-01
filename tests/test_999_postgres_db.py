from timelink.api.database import get_postgres_dbnames
from tests import skip_on_github_actions

# Skip tests if running on Travis CI
pytestmark = skip_on_github_actions


def test_get_dbnames():
    dbnames = get_postgres_dbnames()
    assert len(dbnames) > 0, "No databases found"
