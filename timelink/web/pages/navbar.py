from pages.menu import menu
from contextlib import contextmanager

from nicegui import ui

@contextmanager
def header():
    """Web Interface page frame"""
    with ui.header():
        with ui.row():
            menu()
        ui.space()
        ui.label('Timelink Web Interface').classes('font-bold')
        
    with ui.column().classes('w-full'):
        yield