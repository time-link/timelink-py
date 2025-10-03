import pytest
from timelink.web.pages.homepage import HomePage
from nicegui.testing import User

pytest_plugins = ['nicegui.testing.plugin', 'nicegui.testing.user_plugin']


def test_homepage_init(fake_db, fake_kserver):
    """Test if HomePage stores database and kserver references correctly."""

    page = HomePage(fake_db, fake_kserver)

    assert page.database is fake_db
    assert page.kserver is fake_kserver


@pytest.mark.asyncio
async def test_homepage_view(user: User, fake_db, fake_kserver) -> None:

    HomePage(database=fake_db, kserver=fake_kserver)

    await user.open("/")
    await user.should_see('Welcome to the Timelink Web Interface!')


@pytest.mark.asyncio
async def test_menu_and_navbar_view(user: User, fake_db, fake_kserver) -> None:

    fake_db.table_row_count.return_value = [("attributes", 10), ("entities", 5)]

    HomePage(database=fake_db, kserver=fake_kserver)

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
