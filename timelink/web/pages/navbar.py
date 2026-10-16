from timelink.web.pages.menu import menu
from contextlib import contextmanager

from nicegui import ui, app


@contextmanager
def header(responsive: bool = True):
    """Web Interface page frame"""

    def logout() -> None:
        app.storage.user.clear()
        ui.navigate.to('/login')

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
        ui.link('Project Management', '/project_admin').classes('text-lg font-bold no-underline')
        if app.storage.user["is_admin"]:
            ui.separator()
            ui.link('App Admin', '/admin').classes('text-lg font-bold no-underline')

    with ui.header():
        with ui.row():
            ui.button("Menu", on_click=lambda: left_drawer.toggle()).classes('text-white font-bold no-underline')
            ui.space()
            menu()
        ui.space()
        ui.label('Timelink Web Interface').classes('font-bold text-lg')
        ui.space()
        with ui.row():
            ui.label(f'Logged in as {app.storage.user["username"]}').classes('font-bold mt-2')
            ui.button("Logout", on_click=logout).classes('text-white font-bold no-underline')

    with ui.column().classes('w-full'):
        # IDList mechanism (MHK person_show.vm equivalent): ids saved
        # across pages, carried by a persistent Link preview form
        idlist = app.storage.user.get('idlist', [])
        if idlist:
            def empty_idlist() -> None:
                app.storage.user['idlist'] = []
                ui.navigate.to(ui.context.client.page_path)

            with ui.row().classes('w-full items-center gap-2 bg-amber-100 rounded p-2'):
                ui.icon('playlist_add_check').classes('text-amber-600')
                ui.label(f'IDList: {len(idlist)} saved ids').classes('text-sm font-bold')
                ui.button('Link preview',
                          on_click=lambda: ui.navigate.to('/idlist')
                          ).props('dense unelevated size=sm color=positive')
                ui.button('Empty list', on_click=empty_idlist
                          ).props('dense flat size=sm color=negative')
        yield
