import pytest
from timelink.web.pages.homepage import HomePage
from nicegui.testing import User

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


def test_homepage_init(fake_timelink_app):
    """Test if HomePage stores database and kserver references correctly."""

    page = HomePage(fake_timelink_app)

    assert page.database is fake_timelink_app.database
    assert page.kserver is fake_timelink_app.kleio_server


@pytest.mark.asyncio
async def test_homepage_view(user: User, fake_timelink_app) -> None:

    HomePage(fake_timelink_app.database)

    await user.open("/")
    await user.should_see('Welcome to the Timelink Web Interface!')


@pytest.mark.asyncio
async def test_menu_and_navbar_view(user: User, fake_timelink_app) -> None:

    fake_timelink_app.database.table_row_count.return_value = [("attributes", 10), ("entities", 5)]

    HomePage(fake_timelink_app)

    # Navbar button check
    await user.open("/")
    await user.should_see('Home')
    await user.should_see('Explore')
    await user.should_see('Search')
    await user.should_see('Status')

    # Side menu button check
    await user.should_see('Overview')
    await user.should_see('People')
    await user.should_see('Families')
    await user.should_see('Calendar')
    await user.should_see('Linking')
    await user.should_see('Sources')
    await user.should_see('Search')
    await user.should_see('Admin')
