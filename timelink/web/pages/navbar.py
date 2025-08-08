from pages.menu import menu
from contextlib import contextmanager

from nicegui import ui

@contextmanager
def header():
    """Web Interface page frame"""
    
    with ui.left_drawer(value=False, bordered=True, elevated=True).classes('bg-gray-50').props('width=200') as left_drawer:
        ui.link('Overview', '/overview').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('People', '/people').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Families', '/families').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Calendar', '/calendar').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Linking', '/linking').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Sources', '/sources').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Search', '/search').classes('text-lg font-bold no-underline')
        ui.separator()
        ui.link('Admin', '/admin').classes('text-lg font-bold no-underline')

    with ui.header():
        with ui.row():
            ui.button("Menu", on_click=lambda: left_drawer.toggle()).classes('text-white font-bold no-underline')
            ui.space()
            menu()
        ui.space()
        ui.label('Timelink Web Interface').classes('font-bold')
        
    with ui.column().classes('w-full'):
        yield