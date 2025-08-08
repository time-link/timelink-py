from pages import navbar

from nicegui import ui


class CalendarPage:
    
    """Page for calendar and date displays"""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/calendar')
        async def register():
            await self.calendar_page()


    async def calendar_page(self):
        with navbar.header():
            ui.page_title("Calendar")
            ui.markdown(f'#### **Calendar Page stub**').classes('ml-2 mb-4 text-orange-500')