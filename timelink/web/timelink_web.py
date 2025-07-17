from nicegui import ui, app
import timelink_web_utils
import sys
from contextlib import contextmanager
import asyncio
from explore_tab import ExploreTab

port = 8000
kserver = None
database = None

async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""
    global database, kserver
    kserver, database = await timelink_web_utils.run_setup()


@contextmanager
def disable(button: ui.button):
    button.disable()
    try:
        yield
    finally:
        button.enable()


async def update_from_sources(button: ui.button) -> None:
    """ Attempt to update database from sources."""

    with disable(button):
        ui.notify("Updating database from sources...")
        try:
            await asyncio.to_thread(timelink_web_utils.run_imports_sync, database)
            ui.notify("Done updating the database!", type="positive")
        except Exception as e:
            ui.notify(f"ERROR: Database import failed: {e}", type="negative")


@ui.page('/')
def index():

    ui.add_body_html('''
                <style>
                .highlight-cell { text-decoration: underline dotted; }
                .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                </style>
                ''')

    with ui.header().classes(replace='row items-center'):
        with ui.tabs()as tabs:
            home_tab = ui.tab('home', label="Home")
            explore_tab = ui.tab('explore', label="Explore")
            status_tab = ui.tab('faq', label="Status Check")

    with ui.tab_panels(tabs, value=home_tab).classes('w-full'):

        with ui.tab_panel(home_tab):
            """Home Tab - Timelink Landing page."""
            ui.markdown(f'#### **Welcome to the Timelink Web Interface!**').classes('mb-4 text-orange-500')

        with ui.tab_panel(explore_tab):
            """Explore Tab - Used for an overview of the database."""
            explore_tab_instance = ExploreTab(database, timelink_web_utils, kserver)
            explore_tab_instance.create_ui()


        with ui.tab_panel(status_tab):
            """Currently used as a debug page to check for additional information."""
            with ui.row():
                ui.button("Timelink Server Status", on_click=lambda: timelink_web_utils.show_kleio_info(kserver))
                ui.button("Database Status", on_click=lambda: timelink_web_utils.show_table(database))
                ui.button("Update Database from Sources", on_click=lambda this_button: update_from_sources(this_button.sender))


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])


app.on_startup(initial_setup)
ui.run(title='Timelink Web Interface', port=int(port))