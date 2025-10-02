from nicegui import ui, app
from timelink.web import timelink_web_utils
from timelink.app.backend import TimelinkWebApp, WebAppSettings
import sys
from pathlib import Path

# --- Pages ---
from timelink.web.pages import (homepage, status_page, explore_page,
                                display_id_page, tables_page, overview_page,
                                people_page, families_page, calendar_page,
                                linking_page, sources_page, search_page, admin_page)


port = 8000
kserver = None
database = None
project_path = Path.cwd()  # melhor timelink_path
database_type = "sqlite"
solr_path = 'http://localhost:8983/solr/timelink-core'


async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""
    global database, kserver
    kserver, database, solr_client = await timelink_web_utils.run_setup(project_path, database_type, solr_path)

    # Alternative: delegate all setup work to TimelinkWebApp
    #  and settings setup to Pydantic BaseSettings
    web_settings = WebAppSettings(timelink_home=project_path,
                                  users_db_type=database_type,
                                  timelink_solr_url=solr_path
                                  )
    tlweb = TimelinkWebApp(settings=web_settings)

    kserver = tlweb.kleio_server

    homepage.HomePage(database=database, kserver=kserver)

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

    source_page = sources_page.Sources(database=database, kserver=kserver)

    status_page.StatusPage(database=database, kserver=kserver, sources=source_page)

    search_page.Search(database=database, kserver=kserver, solr_client=solr_client)

    admin_page.Admin(database=database, kserver=kserver)


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])

if "--directory" in sys.argv:
    idx = sys.argv.index("--directory") + 1
    if idx < len(sys.argv):
        project_path = Path(sys.argv[idx]).resolve()

if "--database" in sys.argv:
    idx = sys.argv.index("--database") + 1
    if idx < len(sys.argv):
        database_type = sys.argv[idx]

app.on_startup(initial_setup)

if __name__ in {'__main__', '__mp_main__'}:
    ui.run(title='Timelink Web Interface', port=int(port))
