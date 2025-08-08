from nicegui import ui


def menu() -> None:
    ui.space()
    ui.link('Home', '/').classes('text-white font-bold no-underline mt-2')
    ui.space()
    ui.link('Explore', '/explore').classes('text-white font-bold no-underline mt-2')
    ui.space()
    ui.link('Search', '/search').classes('text-white font-bold no-underline mt-2')
    ui.space()
    ui.link('Server Status', '/status').classes('text-white font-bold no-underline mt-2')