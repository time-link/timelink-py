from nicegui import ui, app
import timelink_web_utils
import sys

# --- Pages ---
from pages import homepage, status_page, explore_page, display_id_page, tables_page

#from explore_tab import ExploreTab

port = 8000
kserver = None
database = None

async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""
    global database, kserver
    kserver, database = await timelink_web_utils.run_setup()
    
    homepage.HomePage()
    
    status_page.StatusPage(database=database, kserver=kserver)
    
    explore_page.ExplorePage(database=database, kserver=kserver)
    
    id_page = display_id_page.DisplayIDPage(database=database, kserver=kserver)
    id_page.register()
    
    table_page = tables_page.TablesPage(database=database, kserver=kserver)
    table_page.register()


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])


app.on_startup(initial_setup)
ui.run(title='Timelink Web Interface', port=int(port))