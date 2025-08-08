from pages import navbar
from nicegui import ui

class Search:
    
    """Page for robust searching. """
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/search')
        async def register():
            await self.search_page()


    async def search_page(self):
        with navbar.header():
            ui.page_title("Search")

            ui.label('Search').classes('text-orange-500 text-xl font-bold')

            with ui.row():
                self.text_input = ui.input(
                    label='You can search for a name, a job, or someting else.', placeholder='e.g. john smith blacksmith coimbra').on('keydown.enter', self._handle_searches).classes('w-80 items-center mb-4')
                ui.button('Search').on('click', self._handle_searches).classes("items-center mt-4 ml-3 mb-4")
    

    def _handle_searches(self):
        """Handles the search by ID function."""
        if self.text_input.value:
            keywords = self.text_input.value.replace(' ', '__').rstrip('__')
            ui.navigate.to(f'/search_tables?keywords={keywords}')
        else:
            ui.notify("You need a valid input to search the database.")