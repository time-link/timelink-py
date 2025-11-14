from timelink.web import timelink_web
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_initial_setup(monkeypatch):

    # Create fake settings to be returned by run_setup
    fake_database = MagicMock()
    fake_job_scheduler = MagicMock()
    fake_settings = SimpleNamespace(
        database=fake_database,
        job_scheduler=fake_job_scheduler
    )

    # Patch run_setup to return the fake settings
    monkeypatch.setattr(
        timelink_web.timelink_web_utils,
        "run_setup",
        AsyncMock(return_value=fake_settings)
    )

    # Patch pages to track instantiation
    page_modules = {
        "login.Login": MagicMock(),
        "homepage.HomePage": MagicMock(),
        "register_page.RegisterPage": MagicMock()
    }

    for path, mock_cls in page_modules.items():
        module_name, class_name = path.split(".")
        module = getattr(timelink_web, module_name)
        monkeypatch.setattr(module, class_name, mock_cls)

    # Run initial setup
    await timelink_web.initial_setup()

    # Check that run_setup was called with correct arguments
    timelink_web.timelink_web_utils.run_setup.assert_awaited_once_with(
        home_path=timelink_web.project_path,
        job_scheduler=timelink_web.job_scheduler,
        database_type=timelink_web.database_type
    )

    # Check that pages were instantiated with timelink_app
    for mock_cls in page_modules.values():
        mock_cls.assert_called_once_with(timelink_app=fake_settings)

    # Check that job scheduler was started
    assert fake_settings.job_scheduler.start.called
