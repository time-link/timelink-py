from nicegui import ui


def menu() -> None:
    ui.link('Home', '/').classes('text-white font-bold no-underline')
    ui.space()
    ui.link('Explore', '/explore').classes('text-white font-bold no-underline')
    ui.space()
    ui.link('Server Status', '/status').classes('text-white font-bold no-underline')