from timelink.web.pages import navbar
from nicegui import ui


class Linking:

    """Page for linking and Entity Resolution."""
    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/linking')
        async def register():
            await self.linking_page()

    async def linking_page(self):
        with navbar.header():
            ui.page_title("Linking")
            ui.markdown('#### **Linking, Entity Resolution and Linked Data**').classes('ml-2 mb-4 text-orange-500')
