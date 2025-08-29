from nicegui import ui, app
from timelink.web import timelink_web_utils
import sys

# --- Pages ---
from timelink.web.pages import (homepage, status_page, explore_page,
                                display_id_page, tables_page, overview_page,
                                people_page, families_page, calendar_page,
                                linking_page, sources_page, search_page, admin_page)


port = 8000
kserver = None
database = None


async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""
    global database, kserver
    kserver, database = await timelink_web_utils.run_setup()

    homepage.HomePage(database=database, kserver=kserver)

    status_page.StatusPage(database=database, kserver=kserver)

    explore_page.ExplorePage(database=database, kserver=kserver)

    id_page = display_id_page.DisplayIDPage(database=database, kserver=kserver)
    id_page.register()

    table_page = tables_page.TablesPage(database=database, kserver=kserver)
    table_page.register()

    overview_page.Overview(database=database, kserver=kserver)

    people_page.PeopleGroupsNetworks(database=database, kserver=kserver)

    families_page.Families(database=database, kserver=kserver)

    calendar_page.CalendarPage(database=database, kserver=kserver)

    linking_page.Linking(database=database, kserver=kserver)

    sources_page.Sources(database=database, kserver=kserver)

    search_page.Search(database=database, kserver=kserver)

    admin_page.Admin(database=database, kserver=kserver)


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])


app.on_startup(initial_setup)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Timelink Web Interface', port=int(port))
