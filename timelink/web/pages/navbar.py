from timelink.web.pages.menu import menu
from contextlib import contextmanager

from nicegui import ui


@contextmanager
def header(responsive: bool = True):
    """Web Interface page frame"""

    drawer_props = ''

    if responsive:
        drawer_props += 'show-if-above breakpoint=1000 width=200'
    else:
        drawer_props += 'width=200'

    with ui.left_drawer(value=responsive, bordered=True, elevated=True).classes('bg-gray-50').props(drawer_props) as left_drawer:
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
