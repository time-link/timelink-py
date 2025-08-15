from pages import navbar

from nicegui import ui


class Sources:
    
    """Page for sources viewing. """
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/sources')
        async def register():
            await self.sources_page()


    async def sources_page(self):
        with navbar.header():
            ui.page_title("Sources")
            ui.label('Sources').classes('text-orange-500 ml-3 mt-4 text-xl font-bold')

            with ui.card().tight().classes("w-full bg-gray-50"):
                with ui.tabs() as tabs:
                    files_tab = ui.tab('files', label='Source Files').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    repository_tab = ui.tab('repository', label='Repository').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    trans_output_tab = ui.tab('translation_output', label='Translation Output').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    import_output_tab = ui.tab('import_output', label='Importer Output').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    help_tab = ui.tab('help', label='Help').classes("w-full bg-gray-70 text-orange-500 font-bold")
                with ui.tab_panels(tabs, value=files_tab).classes('w-full bg-gray-50'):
                    with ui.tab_panel(files_tab).classes("items-center"):
                        ui.label("Files Tab")
                    with ui.tab_panel(repository_tab).classes("items-center"):
                        ui.label("Repository Tab")
                    with ui.tab_panel(trans_output_tab).classes("items-center"):
                        ui.label("Translation Output Tab")
                    with ui.tab_panel(import_output_tab).classes("items-center"):
                        ui.label("Importer Output Tab")
                    with ui.tab_panel(help_tab).classes("items-center"):
                        ui.label("Help Tab")