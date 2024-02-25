from timelink.api.database import get_postgres_dbnames


def test_get_dbnames():
    dbnames = get_postgres_dbnames()
    assert len(dbnames) > 0, "No databases found"
