from timelink.web.pages import navbar

from nicegui import ui


class HomePage:

    def __init__(self, timelink_app) -> None:

        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/')
        def home_page():
            with navbar.header():
                ui.page_title("Timelink Web Home")
                ui.markdown('#### **Welcome to the Timelink Web Interface!**').classes('mb-4 text-orange-500')
