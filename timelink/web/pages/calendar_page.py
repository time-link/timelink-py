from timelink.web.pages import navbar

from nicegui import ui


class CalendarPage:

    """Page for calendar and date displays"""
    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/calendar')
        async def register():
            await self.calendar_page()

    async def calendar_page(self):
        with navbar.header():
            ui.page_title("Calendar")
            ui.markdown('#### **Calendar Page stub**').classes('ml-2 mb-4 text-orange-500')
