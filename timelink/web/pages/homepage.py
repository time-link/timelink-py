from pages import navbar

from nicegui import ui


class HomePage:

    def __init__(self) -> None:
        @ui.page('/')
        def home_page():
            with navbar.header():
                ui.page_title("Timelink Web Home")
                ui.markdown(f'#### **Welcome to the Timelink Web Interface!**').classes('mb-4 text-orange-500')