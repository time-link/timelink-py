"""Regression tests for /tables/attributes against a REAL database.

The other tests for this page mock session.execute, which is why a
500 from selecting phantom columns (`nattributes.c.sex`) survived CI.
These tests run the actual view SQL against an in-memory SQLite
database seeded through the ORM.
"""

# pylint: disable=import-error
from types import SimpleNamespace

import pytest
from nicegui.testing import User

from timelink.api.database import TimelinkDatabase
from timelink.api.models import base  # pylint: disable=unused-import # noqa: F401
from timelink.api.models.attribute import Attribute
from timelink.api.models.person import Person
from timelink.web.pages import tables_page

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


@pytest.fixture()
def seeded_app():
    """Real TimelinkDatabase with a person carrying an accented attribute."""
    database = TimelinkDatabase(
        db_name="tables_attr_test", db_type="sqlite", db_path=None
    )
    with database.session() as session:
        person = Person(
            id="test-per1", name="maria fc", sex="f", groupname="n"
        )
        session.add(person)
        session.flush()
        for i, value in enumerate(["capitão", "capitao", "Capitão"]):
            session.add(
                Attribute(
                    id=f"test-attr{i}",
                    entity="test-per1",
                    the_type="cargo",
                    the_value=value,
                    the_date="1650-01-01",
                )
            )
        session.commit()

    # minimal app stub: real database, mock the rest
    from unittest.mock import MagicMock

    app = SimpleNamespace(
        database=database,
        solr_manager=None,
        search_backend=MagicMock(),
        kleio_server=None,
        users_db=MagicMock(),
    )
    yield app
    database.session().close()
    database.drop_db()


@pytest.mark.asyncio
async def test_attributes_page_no_500(user: User, seeded_app, fake_user):
    """Selecting from the nattributes view must not raise (bug: sex/pobs)."""
    tables_page.TablesPage(seeded_app).register()
    await user.open("/tables/attributes?attr_type=cargo")
    await user.should_see("Entries with attribute cargo")


@pytest.mark.asyncio
async def test_attribute_drilldown_matches_accents(user: User, seeded_app, fake_user):
    """Clicking value 'capitão' must find the rows (accent-insensitive)."""
    from nicegui import ui as nicegui_ui

    tables_page.TablesPage(seeded_app).register()
    await user.open("/tables/attributes?attr_type=cargo&attr_value=capit%C3%A3o")

    grids = user.find(nicegui_ui.aggrid).elements
    assert grids, "attributes grid not rendered"
    rows = None
    for grid in grids:
        options = grid.options or {}
        fields = {col.get("field") for col in options.get("columnDefs", [])}
        if "Cargo" in fields:
            rows = options.get("rowData") or []
            break
    assert rows is not None, "attributes grid with Cargo column not found"
    # all three source variants of the value must survive the filter
    values = {row["Cargo"] for row in rows}
    assert values == {"capitão", "capitao", "Capitão"}
