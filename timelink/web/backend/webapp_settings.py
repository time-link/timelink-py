"""Pydantic settings for the timelink web app.

Salvaged from the ``test-jrc-web-merge`` branch
(``timelink/app/backend/webapp_settings.py``). Values can be set via
environment variables with the same name as the fields; see
https://docs.pydantic.dev/latest/concepts/pydantic_settings/

Sample usage:

    settings = WebAppSettings(timelink_users_db_type="postgres")

Note: secrets are handled separately — ``TIMELINK_ADMIN_PASSWORD``,
``TIMELINK_STORAGE_SECRET``, ``GITHUB_CLIENT_ID``/``GITHUB_CLIENT_SECRET``
are read directly from the environment (see timelink_web.py and
timelink_app_wrapper.py).
"""
from pydantic_settings import BaseSettings


class WebAppSettings(BaseSettings):
    """Timelink web app settings."""

    timelink_app_name: str = "Timelink"
    timelink_admin_email: str = "joaquim@uc.pt"
    timelink_users_db_type: str = "sqlite"
    timelink_users_db_name: str = "timelink_users.sqlite"
    timelink_app_url: str = "http://localhost:8000"
    timelink_users_db_path: str = ""
    timelink_solr_url: str = "http://localhost:8983"
