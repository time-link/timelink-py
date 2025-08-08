from pages import navbar

from nicegui import ui


class Sources:
    
    """Page for sources viewing. """
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/sources')
        async def register():
            await self.sources_page()


    async def sources_page(self):
        with navbar.header():
            ui.page_title("Sources")
            ui.markdown(f'#### **Sources Page**').classes('ml-2 mb-4 text-orange-500')