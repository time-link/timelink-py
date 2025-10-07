import pytest
from timelink.web.pages.overview_page import Overview
from nicegui.testing import User
import pandas as pd
from unittest.mock import MagicMock

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


def test_overview_init(fake_timelink_app):
    """Test if Overview page stores database and kserver references correctly."""

    page = Overview(fake_timelink_app)

    assert page.database is fake_timelink_app.database
    assert page.kserver is fake_timelink_app.kleio_server


@pytest.mark.asyncio
async def test_overview_main_view(user: User, fake_timelink_app) -> None:
    """Check for elements within the page that are always present independent of database state."""

    Overview(fake_timelink_app)

    await user.open("/overview")
    await user.should_see('Database Overview')
    await user.should_see('Entity Count')
    await user.should_see('Latest Source Status')
    await user.should_see('Recently Viewed')
    await user.should_see('Important Entities')
    await user.should_see('Recent Searches')


@pytest.mark.asyncio
async def test_display_entity_count_success(user, fake_timelink_app, monkeypatch):
    """Test if entities are being correctly counted."""

    df = pd.DataFrame({
        "pom_class": ["geoentity", "person", "act", "other"],
        "count": [5, 10, 3, 1],
    })

    monkeypatch.setattr("timelink.web.pages.overview_page.timelink_web_utils.get_entity_count_table", lambda _: df)

    # Patch aggrid to capture input and check data inside would-be grid.
    captured = {}

    def fake_aggrid(options):
        captured.update(options)
        return MagicMock()

    monkeypatch.setattr("timelink.web.pages.overview_page.ui.aggrid", fake_aggrid)

    Overview(fake_timelink_app)

    # Visible to user
    await user.open("/overview")
    await user.should_see("Total number of entities:")
    await user.should_see("18")

    # internal data passed to AgGrid
    assert "rowData" in captured
    row_classes = [row["pom_class"] for row in captured["rowData"]]
    assert "geoentity" in row_classes
    assert "person" in row_classes
    assert "act" in row_classes
    assert "other" in row_classes


@pytest.mark.asyncio
async def test_display_entity_count_failure(user, fake_timelink_app, monkeypatch):
    """Throw an error in display_entity_count to check for correct error output."""

    # force an exception
    def bad_get_table(db):
        raise RuntimeError("Huge Database Error!")

    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_entity_count_table",
        bad_get_table
    )

    page = Overview(fake_timelink_app)
    page._display_entity_count()

    # User should see error message
    await user.open("/overview")
    await user.should_see("Could not load entity count - something went wrong: (Huge Database Error!)")


@pytest.mark.asyncio
async def test_display_sources_count_success(user: User, fake_timelink_app, monkeypatch):
    """Check that _display_sources_count renders a table correctly."""

    # fake sources DataFrame
    df = pd.DataFrame({
        "name": ["Source A", "Source B"],
        "path": ["path/a", "path/b"],
        "nerrors": [1, 0],
        "error_rpt": ["Error: error1", ""],
        "nwarnings": [2, 1],
        "warning_rpt": ["2 Warnings", "No warnings"],
        "imported": ["2025-01-01", "2025-01-02"],
        "structure": ["gacto2", "gacto3"],
        "translator": ["T1", "T2"],
        "translation_date": ["2025-01-03", "2025-01-04"]
    })

    # patch the function to return the fake DataFrame
    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_recent_sources",
        lambda db: df
    )

    # capture aggrid call
    captured_aggrid = {}

    def fake_aggrid(options):
        captured_aggrid.update(options)
        return MagicMock(on=lambda event, func: None, classes=lambda x: None)

    monkeypatch.setattr("timelink.web.pages.overview_page.ui.aggrid", fake_aggrid)

    page = Overview(fake_timelink_app)
    page._display_sources_count()

    # check that rowData matches the DataFrame
    assert captured_aggrid["rowData"] == df.to_dict("records")
    assert "columnDefs" in captured_aggrid
    # optionally check one column exists
    assert any(col["field"] == "name" for col in captured_aggrid["columnDefs"])


@pytest.mark.asyncio
async def test_display_sources_count_failure(user, fake_timelink_app, monkeypatch):
    """Check that _display_sources_count shows an error if the function fails."""

    # force an exception
    def bad_get_sources(db):
        raise RuntimeError("Fetched miserably...")

    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_recent_sources",
        bad_get_sources
    )

    page = Overview(fake_timelink_app)
    page._display_sources_count()

    # User should see error message
    await user.open("/overview")
    user.find("Latest Source Status").click()
    await user.should_see("Could not load recent sources - something went wrong: (Fetched miserably...)")


@pytest.mark.asyncio
async def test_display_recent_views_success(user, fake_timelink_app, monkeypatch):
    """Check that _display_recent_views renders a table correctly."""

    df = pd.DataFrame([
        {
            "entity_id": "geo-1",
            "entity_type": "geoentity",
            "activity_type": "viewed",
            "desc": "Viewed geo-1",
            "when": "2025-09-02 12:00:00.000"
        },
        {
            "entity_id": "person-1",
            "entity_type": "source",
            "activity_type": "viewed",
            "desc": "Viewed person-1",
            "when": "2025-09-02 13:00:00.000"
        },
    ])

    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_recent_history",
        lambda db, searched_only=False: df
    )

    captured_aggrids = []

    def fake_aggrid(options):
        captured_aggrids.append(options)
        return MagicMock(on=lambda event, func: None, classes=lambda x: None)

    monkeypatch.setattr("timelink.web.pages.overview_page.ui.aggrid", fake_aggrid)

    Overview(fake_timelink_app)
    await user.open("/overview")

    # Get the grid that is rendered when the tab is clicked.
    user.find("Recently Viewed").click()
    search_grid = captured_aggrids[-1]

    # Assert data matches
    expected_cols = ["entity_id", "entity_type", "activity_type", "desc", "when"]
    expected_values = ["geo-1", "geoentity", "viewed", "Viewed geo-1"]
    actual_cols = [col["field"] for col in search_grid["columnDefs"]]
    row_values = [val for row in search_grid["rowData"] for val in row.values()]

    assert actual_cols == expected_cols
    assert all(v in row_values for v in expected_values)


@pytest.mark.asyncio
async def test_display_important_entities_success(user, fake_timelink_app, monkeypatch):
    """Check that _display_important_entities renders a table correctly."""

    df = pd.DataFrame([
        {
            "entity_id": "geo-1",
            "entity_type": "geoentity",
            "activity_type": "viewed",
            "desc": "Viewed geo-1",
            "when": "2025-09-02 12:00:00.000"
        },
        {
            "entity_id": "person-1",
            "entity_type": "source",
            "activity_type": "viewed",
            "desc": "Viewed person-1",
            "when": "2025-09-02 13:00:00.000"
        },
        {
            "entity_id": "geo-1",
            "entity_type": "geoentity",
            "activity_type": "viewed",
            "desc": "Viewed geo-1 again",
            "when": "2025-09-02 14:00:00.000"
        },
    ])

    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_recent_history",
        lambda db: df
    )

    captured_aggrids = []

    def fake_aggrid(options):
        captured_aggrids.append(options)
        return MagicMock(on=lambda event, func: None, classes=lambda x: None)

    monkeypatch.setattr("timelink.web.pages.overview_page.ui.aggrid", fake_aggrid)

    Overview(fake_timelink_app)
    await user.open("/overview")

    # Only consider the last aggrid call
    user.find("Important Entities").click()
    imp_grid = captured_aggrids[-1]

    expected_cols = ["entity_id", "entity_type", "number_of_accesses"]
    expected_values = ["geo-1", "person-1", "geoentity", "source", 2, 1]

    # Check data
    actual_cols = [col["field"] for col in imp_grid["columnDefs"]]
    row_values = [val for row in imp_grid["rowData"] for val in row.values()]

    assert actual_cols == expected_cols
    assert all(v in row_values for v in expected_values)


@pytest.mark.asyncio
async def test_display_recent_searches_success(user, fake_timelink_app, monkeypatch):
    """Check that _display_recent_searches renders a table correctly."""

    df = pd.DataFrame([
        {"entity_id": "ana", "entity_type": "All Entities", "activity_type": "searched",
         "desc": "Found 17 results with this search.", "when": "2025-08-29 14:03:17.400876"},
        {"entity_id": "ana", "entity_type": "Persons", "activity_type": "Name search",
         "desc": "Between 0001-01-01 and 9999-12-31 - Found 11 results.", "when": "2025-08-29 13:47:56.244831"},
        {"entity_id": "SELECT * FROM entities LIMIT 50", "entity_type": "entities", "activity_type": "SQL search",
         "desc": "Found 50 results with this search.", "when": "2025-08-26 11:09:33.443085"},
        {"entity_id": "Joao", "entity_type": "Persons", "activity_type": "Name search (exact)",
         "desc": "Between 0001-01-01 and 9999-12-31 - Found 3 results.", "when": "2025-08-25 10:49:26.569238"}
    ])

    monkeypatch.setattr(
        "timelink.web.pages.overview_page.timelink_web_utils.get_recent_history",
        lambda db, searched_only=True: df
    )

    captured_aggrids = []

    def fake_aggrid(options):
        captured_aggrids.append(options)
        return MagicMock(on=lambda event, func: None, classes=lambda x: None)

    monkeypatch.setattr("timelink.web.pages.overview_page.ui.aggrid", fake_aggrid)

    Overview(fake_timelink_app)
    await user.open("/overview")

    # Click "Recent Searches" tab to render
    user.find("Recent Searches").click()
    search_grid = captured_aggrids[-1]

    expected_cols = ["entity_id", "entity_type", "activity_type", "desc", "when"]
    expected_values = ["ana", "Joao", "All Entities", "Persons", "searched", "SQL search"]

    actual_cols = [col["field"] for col in search_grid["columnDefs"]]
    row_values = [val for row in search_grid["rowData"] for val in row.values()]

    assert actual_cols == expected_cols
    assert all(v in row_values for v in expected_values)


@pytest.mark.asyncio
async def test_handle_search_results_click(fake_timelink_app, monkeypatch):
    """Test navigation based on activity_type in _handle_search_results_click."""

    # Mock ui.navigate.to
    navigated_to = {}
    monkeypatch.setattr("timelink.web.pages.overview_page.ui.navigate.to", lambda url: navigated_to.update({"url": url}))

    class AppStorage:
        tab = {}
    monkeypatch.setattr("timelink.web.pages.overview_page.app", AppStorage())

    page = Overview(fake_timelink_app)

    events = [
        {
            "args": {
                "colId": "entity_id",
                "data": {
                    "activity_type": "searched",
                    "entity_id": "ana",
                    "entity_type": "All Entities",
                    "desc": "Found 17 results"
                }
            }
        },
        {
            "args": {
                "colId": "entity_id",
                "data": {
                    "activity_type": "SQL search",
                    "entity_id": "SELECT * FROM entities LIMIT 50",
                    "entity_type": "entities",
                    "desc": "Found 50 results"
                }
            }
        },
        {
            "args": {
                "colId": "entity_id",
                "data": {
                    "activity_type": "Name search",
                    "entity_id": "Joao",
                    "entity_type": "Persons",
                    "desc": "Between 2025-01-01 and 2025-12-31"
                }
            }
        },
        {
            "args": {
                "colId": "entity_id",
                "data": {
                    "activity_type": "Name search (exact)",
                    "entity_id": "Joao",
                    "entity_type": "Persons",
                    "desc": "Between 2025-01-01 and 2025-12-31"
                }
            }
        },
    ]

    # Test searched
    page._handle_search_results_click(MagicMock(**events[0]))
    assert navigated_to["url"] == '/search_tables?keywords=ana&tables=All Entities'

    # Test SQL search
    page._redo_sql_query = MagicMock()
    page._handle_search_results_click(MagicMock(**events[1]))
    page._redo_sql_query.assert_called_once_with("SELECT * FROM entities LIMIT 50", "entities")

    # Test Name search
    page._handle_search_results_click(MagicMock(**events[2]))
    assert navigated_to["url"] == '/search_names?names=Joao&from_=2025-01-01&to_=2025-12-31'

    # Test Name search (exact)
    page._handle_search_results_click(MagicMock(**events[3]))
    assert navigated_to["url"] == '/search_names?names=Joao&from_=2025-01-01&to_=2025-12-31&exact=1'


@pytest.mark.asyncio
async def test_redo_sql_query(fake_timelink_app, monkeypatch):
    """Test that _redo_sql_query stores values and navigates correctly."""

    navigated_to = {}
    monkeypatch.setattr("timelink.web.pages.overview_page.ui.navigate.to", lambda url: navigated_to.update({"url": url}))

    class FakeStorage:
        tab = {}

    class FakeApp:
        storage = FakeStorage()

    monkeypatch.setattr("timelink.web.pages.overview_page.app", FakeApp())

    page = Overview(fake_timelink_app)
    page._redo_sql_query("SELECT 1", "entities")

    assert FakeApp.storage.tab["sql_table"] == "entities"
    assert FakeApp.storage.tab["sql_query"] == "SELECT 1"
    assert navigated_to["url"] == "/search_tables_sql"
