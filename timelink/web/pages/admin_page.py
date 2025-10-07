from timelink.web.pages import navbar

from nicegui import ui


class Admin:

    """Page for Administration settings. """
    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/admin')
        async def register():
            await self.admin_page()

    async def admin_page(self):
        with navbar.header():
            ui.page_title("Admin")
            ui.markdown('#### **Admin configuration page.**').classes('ml-2 mb-4 text-orange-500')
