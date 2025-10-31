from timelink.web import timelink_web

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_initial_setup(monkeypatch):

    fake_database = MagicMock()
    fake_job_scheduler = MagicMock()
    fake_settings = SimpleNamespace(
        database=fake_database,
        job_scheduler=fake_job_scheduler
    )

    monkeypatch.setattr(
        timelink_web.timelink_web_utils,
        "run_setup",
        AsyncMock(return_value=fake_settings)
    )

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
        "search_page.Search"
    ]

    for path in page_mocks:
        module_name, class_name = path.split(".")
        module = getattr(timelink_web, module_name)
        mock_instance = MagicMock()
        mock_instance.register = MagicMock()

        # Patch the class to return the mock instance when called
        monkeypatch.setattr(module, class_name, MagicMock(return_value=mock_instance))

    mock_admin_instance = MagicMock()
    monkeypatch.setattr(timelink_web, "Admin", MagicMock(return_value=mock_admin_instance))
    monkeypatch.setattr(timelink_web, "ModelView", MagicMock())

    await timelink_web.initial_setup()

    # Check that page classes were instantiated and register() was called for relevant pages
    for path in page_mocks:
        module_name, class_name = path.split(".")
        cls = getattr(getattr(timelink_web, module_name), class_name)

        if class_name == "StatusPage":
            cls.assert_called_once()
            _, kwargs = cls.call_args
            assert kwargs["timelink_app"] is fake_settings
            assert "sources" in kwargs

        elif class_name == "Sources":
            cls.assert_called_once_with(timelink_app=fake_settings)

        elif class_name == "Search":
            cls.assert_called_once_with(timelink_app=fake_settings)

        else:
            cls.assert_called_once_with(timelink_app=fake_settings)

        # Check if register() was called for relevant pages
        if class_name in ["DisplayIDPage", "TablesPage"]:
            cls.return_value.register.assert_called_once()

        # Check Admin setup called correctly
        timelink_web.Admin.assert_called_once_with(engine=fake_database.engine)
        timelink_web.ModelView.assert_any_call(timelink_web.User)
        timelink_web.ModelView.assert_any_call(timelink_web.UserProperty)
        timelink_web.ModelView.assert_any_call(timelink_web.Project)
        timelink_web.ModelView.assert_any_call(timelink_web.ProjectAccess)
        mock_admin_instance.mount_to.assert_called_once()
        fake_job_scheduler.start.assert_called_once()


def test_port_argument(monkeypatch):
    # Test that the port is read from sys.argv
    monkeypatch.setattr(sys, "argv", ["timelink_web.py", "--port", "1234"])
    import importlib
    importlib.reload(timelink_web)
    assert timelink_web.port == 1234
