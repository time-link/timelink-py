from pages import navbar

from nicegui import ui


class Families:
    
    """Page for Families, Genealogies and Demography"""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/families')
        async def register():
            await self.families_page()


    async def families_page(self):
        with navbar.header():
            ui.page_title("Families, Genealogies and Demography")
            ui.markdown(f'#### **Families, Genealogies and Demography Page**').classes('ml-2 mb-4 text-orange-500')