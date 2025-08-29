from timelink.web.pages import navbar
from timelink.web import timelink_web_utils
from nicegui import ui
from contextlib import contextmanager
import asyncio


class StatusPage:

    """Currently used as a debug page to check for additional information."""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/status')
        def page():
            self.status_page()

    def status_page(self):
        with navbar.header():
            with ui.row():
                ui.page_title("Server and Database Status")
                ui.button("Timelink Server Status", on_click=lambda: timelink_web_utils.show_kleio_info(self.kserver))
                ui.button("Database Status", on_click=lambda: timelink_web_utils.show_table(self.database))
                ui.button("Update Database from Sources", on_click=lambda this_button: self.update_from_sources(this_button.sender))

    @contextmanager
    def disable(self, button: ui.button):
        button.disable()
        try:
            yield
        finally:
            button.enable()

    async def update_from_sources(self, button: ui.button) -> None:
        """ Attempt to update database from sources."""
        with self.disable(button):
            ui.notify("Updating database from sources...")
            try:
                await asyncio.to_thread(timelink_web_utils.run_imports_sync, self.database)
                ui.notify("Done updating the database!", type="positive")
            except Exception as e:
                ui.notify(f"ERROR: Database import failed: {e}", type="negative")
