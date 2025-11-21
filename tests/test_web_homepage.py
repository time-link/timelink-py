import pytest
from timelink.web.pages.homepage import HomePage
from nicegui.testing import User
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


@pytest.mark.asyncio
async def test_homepage_view(user: User, fake_timelink_app, fake_user) -> None:

    # Mock user's projects
    fake_projects = [SimpleNamespace(name="Project A"), SimpleNamespace(name="Project B")]
    fake_timelink_app.users_db.get_user_projects.return_value = fake_projects
    fake_timelink_app.current_project_name = "Project A"
    fake_timelink_app.projects_loaded = True

    # Initialize the homepage
    HomePage(fake_timelink_app)

    # Open homepage
    await user.open("/")

    # Check that the welcome message appears with the username
    await user.should_see(f"Welcome to the Timelink Web Interface, {fake_user['username']}!")
    await user.should_see(f"You are browsing {fake_timelink_app.current_project_name}!")


@pytest.mark.asyncio
async def test_menu_and_navbar_view(user: User, fake_timelink_app, fake_user) -> None:

    fake_projects = [SimpleNamespace(name="Project A"), SimpleNamespace(name="Project B")]
    fake_timelink_app.users_db.get_user_projects.return_value = fake_projects
    fake_timelink_app.current_project_name = "Project A"
    fake_timelink_app.projects_loaded = True

    fake_timelink_app.database.table_row_count.return_value = [("attributes", 10), ("entities", 5)]

    HomePage(fake_timelink_app)

    # Navbar button check
    await user.open("/")
    await user.should_see('Home')
    await user.should_see('Explore')
    await user.should_see('Search')

    # Side menu button check
    await user.should_see('Overview')
    await user.should_see('People')
    await user.should_see('Families')
    await user.should_see('Calendar')
    await user.should_see('Linking')
    await user.should_see('Sources')
    await user.should_see('Search')
    await user.should_see('Project Management')


@pytest.mark.asyncio
async def test_menu_and_navbar_view_admin(user: User, fake_timelink_app, fake_admin) -> None:

    fake_projects = [SimpleNamespace(name="Project A"), SimpleNamespace(name="Project B")]
    fake_timelink_app.users_db.get_user_projects.return_value = fake_projects
    fake_timelink_app.current_project_name = "Project A"
    fake_timelink_app.projects_loaded = True

    fake_timelink_app.database.table_row_count.return_value = [("attributes", 10), ("entities", 5)]

    HomePage(fake_timelink_app)

    await user.open("/")
    await user.should_see('Admin')
