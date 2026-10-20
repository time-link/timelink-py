"""Test the linking management page (list of real entities and occurrences)."""

import pytest
from nicegui.testing import User

from timelink.web.pages import linking_page

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']

FAKE_RENTITIES = [
    {
        "rid": "rp1", "user": "test_user", "status": "MANUAL",
        "description": None, "n_occurrences": 2,
        "occurrences": ["p1", "p2"],
    },
]

FAKE_LINKS = [
        {"entity": "p1", "class": "person", "user": "test_user", "status": "MANUAL", "rule": ""},
        {"entity": "p2", "class": "person", "user": "test_user", "status": "MANUAL", "rule": ""},
]


@pytest.mark.asyncio
async def test_linking_page_shows_rentities(
    user: User, fake_timelink_app, fake_user, monkeypatch
) -> None:
    monkeypatch.setattr(
        linking_page.linking, "list_rentities",
        lambda session, user=None: FAKE_RENTITIES if user in (None, "test_user") else [],
    )
    monkeypatch.setattr(
        linking_page.linking, "rentity_links", lambda session, rid: FAKE_LINKS
    )

    linking_page.Linking(timelink_app=fake_timelink_app)
    await user.open("/linking")

    await user.should_see("rp1")
    await user.should_see("test_user")
    # occurrence rows are inside the expansion; open it
    user.find("rp1 — 2 occurrence(s)").click()

    from nicegui import ui
    tables = list(user.find(ui.table).elements)
    rentity_tables = [t for t in tables if t.row_key == "rid"]
    assert rentity_tables and any(row["rid"] == "rp1" for row in rentity_tables[0].rows)
    occ_tables = [t for t in tables if t.row_key == "entity"]
    assert occ_tables, "occurrence table not rendered"
    assert {row["entity"] for row in occ_tables[-1].rows} == {"p1", "p2"}
    assert all(row["user"] == "test_user" for row in occ_tables[-1].rows)
