
from tests import skip_on_travis
from timelink.api.database import get_dbnames

@skip_on_travis
def test_get_dbnames():
    dbnames = get_dbnames()
    assert len(dbnames) > 0, "No databases found"