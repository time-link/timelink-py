from timelink.web.pages import navbar
from nicegui import ui


class PeopleGroupsNetworks:

    """Page for People, Groups and Networks"""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/people')
        async def register():
            await self.people_page()

    async def people_page(self):
        with navbar.header():
            ui.page_title("People, Groups and Networks")
            ui.markdown('#### **People, Groups and Networks Page**').classes('ml-2 mb-4 text-orange-500')
