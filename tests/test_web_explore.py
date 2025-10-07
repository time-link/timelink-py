import pytest
from timelink.web.pages.explore_page import ExplorePage
from nicegui.testing import User
from nicegui import ElementFilter, ui
from timelink.web import timelink_web_utils
import pandas as pd
from unittest.mock import MagicMock

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


def test_explore_init(fake_timelink_app):
    """Test if HomePage stores database and kserver references correctly."""

    page = ExplorePage(fake_timelink_app)

    assert page.database is fake_timelink_app.database
    assert page.kserver is fake_timelink_app.kleio_server


@pytest.mark.asyncio
async def test_explore_main_view(user: User, fake_timelink_app) -> None:
    """Check for elements within the page that are always present independent of database state."""

    ExplorePage(timelink_app=fake_timelink_app)

    await user.open("/explore")
    await user.should_see('Search by ID')
    await user.should_see('Names')
    await user.should_see('Attributes')
    await user.should_see('Functions')
    await user.should_see('Relations')
    await user.should_see('Advanced Options')
    await user.should_see('Show Sources')


@pytest.mark.asyncio
async def test_explore_main_view_no_data(user: User, fake_timelink_app, monkeypatch) -> None:
    """Check if attributes, functions and relations display no data correctly if none is to be found in the database."""

    monkeypatch.setattr(timelink_web_utils, "load_data", lambda query, db: None)
    ExplorePage(timelink_app=fake_timelink_app)

    await user.open("/explore")
    with user:
        elements = list(ElementFilter(kind=ui.label, content="No data found."))
        assert len(elements) == 3


@pytest.mark.asyncio
async def test_explore_main_view_with_data(user, fake_timelink_app, monkeypatch):
    """Check if attributes, functions, and relations display correctly when data is available."""

    attr_df = pd.DataFrame({
        "the_type": ["activa", "alcunha"],
        "count": [163, 2],
        "distinct_value": [2, 1]
    })
    func_df = pd.DataFrame({
        "the_value": ["geo1", "geo2"],
        "count": [18, 62]
    })
    rel_df = pd.DataFrame({
        "the_type": ["function-in-act", "geografica"],
        "count": [469, 4],
        "distinct_value": [14, 1]
    })

    def fake_load_data(query, db):
        if query == "attributes":
            return attr_df
        elif query == "functions":
            return func_df
        elif query == "relations":
            return rel_df
        return pd.DataFrame()

    monkeypatch.setattr(timelink_web_utils, "load_data", fake_load_data)

    ExplorePage(timelink_app=fake_timelink_app)

    await user.open("/explore")

    with user:
        attr_labels = [e for e in ElementFilter(kind=ui.label) if e.text in ["activa", "alcunha"]]
        assert len(attr_labels) == 2

        func_labels = [e for e in ElementFilter(kind=ui.label) if e.text in ["geo1", "geo2"]]
        assert len(func_labels) == 2

        rel_labels = [e for e in ElementFilter(kind=ui.label) if e.text in ["function-in-act", "geografica"]]
        assert len(rel_labels) == 2

        counts = ["163", "2", "18", "62", "469", "4"]
        count_labels = [e for e in ElementFilter(kind=ui.label) if e.text in counts]
        assert len(count_labels) == len(counts)


@pytest.mark.asyncio
async def test_explore_search_by_id(user, fake_timelink_app, monkeypatch):
    """Test Search by ID functionality"""

    mock_handler = MagicMock()
    monkeypatch.setattr(ExplorePage, "_handle_id_search", mock_handler)
    ExplorePage(fake_timelink_app)

    await user.open("/explore")

    with user:
        user.find('Explore Database').trigger("keydown.enter")
        assert mock_handler.call_count == 1


@pytest.mark.asyncio
async def test_explore_advanced_search(user, fake_timelink_app, monkeypatch):
    """Test Search by ID functionality"""

    mock_handler = MagicMock()
    monkeypatch.setattr(ExplorePage, "_handle_advanced_search", mock_handler)
    ExplorePage(fake_timelink_app)

    await user.open("/explore")

    with user:
        user.find('Choose Attribute Type').trigger("keydown.enter")
        user.find('Choose Attribute Value').trigger("keydown.enter")
        assert mock_handler.call_count == 2


@pytest.mark.asyncio
async def test_explore_search_handlers(fake_timelink_app, monkeypatch):
    """Test ID/advanced search handlers with empty and filled inputs."""

    # Patch ui.navigate.to and ui.notify so we can track calls
    mock_navigate = MagicMock()
    mock_notify = MagicMock()
    monkeypatch.setattr("nicegui.ui.navigate.to", mock_navigate)
    monkeypatch.setattr("nicegui.ui.notify", mock_notify)

    page = ExplorePage(fake_timelink_app)

    # ---- Test ID search ----
    # Empty input
    page.text_input = MagicMock(value='')
    page._handle_id_search()
    mock_navigate.assert_not_called()
    mock_notify.assert_called_once_with("You need a valid input to search the database.")
    mock_notify.reset_mock()

    # Filled input
    page.text_input.value = 'some-id-here'
    page._handle_id_search()
    mock_navigate.assert_called_once_with('/id/some-id-here')
    mock_navigate.reset_mock()

    # ---- Test Advanced search ----
    # Empty inputs
    page.attribute_type_search = MagicMock(value='')
    page.attribute_value_search = MagicMock(value='')
    page._handle_advanced_search()
    mock_navigate.assert_not_called()
    mock_notify.assert_called_once_with("You need both attribute type and value to search!")
    mock_notify.reset_mock()

    # Filled inputs
    page.attribute_type_search.value = 'type1'
    page.attribute_value_search.value = 'value1'
    page._handle_advanced_search()
    mock_navigate.assert_called_once_with('/tables/persons?value=type1&type=value1')
