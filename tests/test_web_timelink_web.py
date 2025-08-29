from timelink.web import timelink_web

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_initial_setup(monkeypatch):

    fake_kserver = MagicMock()
    fake_db = MagicMock()
    monkeypatch.setattr(timelink_web.timelink_web_utils, "run_setup", AsyncMock(return_value=(fake_kserver, fake_db)))

    page_mocks = [
        "homepage.HomePage",
        "status_page.StatusPage",
        "explore_page.ExplorePage",
        "display_id_page.DisplayIDPage",
        "tables_page.TablesPage",
        "overview_page.Overview",
        "people_page.PeopleGroupsNetworks",
        "families_page.Families",
        "calendar_page.CalendarPage",
        "linking_page.Linking",
        "sources_page.Sources",
        "search_page.Search",
        "admin_page.Admin"
    ]

    for path in page_mocks:
        module_name, class_name = path.split(".")
        module = getattr(timelink_web, module_name)
        mock_instance = MagicMock()
        mock_instance.register = MagicMock()
        
        # Patch the class to return the mock instance when called
        monkeypatch.setattr(module, class_name, MagicMock(return_value=mock_instance))

    await timelink_web.initial_setup()
    assert timelink_web.kserver is fake_kserver
    assert timelink_web.database is fake_db

    # Check that page classes were instantiated and register() was called for relevant pages
    for path in page_mocks:
        module_name, class_name = path.split(".")
        cls = getattr(getattr(timelink_web, module_name), class_name)
        

        cls.assert_called_once_with(database=fake_db, kserver=fake_kserver)

        # Check if register() was called for relevant pages
        if class_name in ["DisplayIDPage", "TablesPage"]:
            cls.return_value.register.assert_called_once()



def test_port_argument(monkeypatch):
    # Test that the port is read from sys.argv
    monkeypatch.setattr(sys, "argv", ["timelink_web.py", "--port", "1234"])
    import importlib
    importlib.reload(timelink_web)
    assert timelink_web.port == 1234