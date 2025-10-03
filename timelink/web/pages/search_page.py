from timelink.web.pages import navbar
from timelink.web import timelink_web_utils
from nicegui import ui, app
import pandas as pd
from sqlalchemy import text, inspect
from timelink.kleio.utilities import format_timelink_date


class Search:

    """Page for robust searching. """
    def __init__(self, database, kserver, solr_manager) -> None:
        self.database = database
        self.kserver = kserver
        self.solr_manager = solr_manager

        @ui.page('/search')
        async def register():
            await self.search_page()

        @ui.page('/advanced_search')
        async def register_advanced():
            await self.advanced_search()

    async def search_page(self):
        with navbar.header():
            ui.page_title("Search")

            # Regular Search
            ui.label('Search').classes('text-orange-500 text-xl ml-3 mt-4 font-bold')

            with ui.row():
                self.text_input = ui.input(
                    label='You can search for a name, a job, or someting else.',
                    placeholder='e.g. john smith blacksmith coimbra'
                ).on('keydown.enter', self._handle_searches).classes('w-80 ml-3')

                ui.button('Search').on('click', self._handle_searches).classes("items-center ml-3 mt-2")

            self.selector = ui.radio(
                ["All Entities", "Real Persons", "Persons", "Acts"], value="All Entities"
            ).props('inline').classes("w-full")

            ui.label("Advanced Search").on(
                'click', lambda : ui.navigate.to('/advanced_search')
            ).classes('text-blue-500 ml-3 mb-2 cursor-pointer text-sm underline italic')

            ui.separator()

            # SQL Search
            ui.label('SQL Search').classes('text-orange-500 text-xl mt-3 ml-3 font-bold')

            @ui.refreshable
            def preview_table_display(table_name: str) -> None:
                """Refreshable table preview on the Search page"""

                if not table_name:
                    return

                self.sql_input.value = f"SELECT * FROM {table_name} LIMIT 50"
                # Preview rows
                query = text(f"SELECT * FROM {table_name} LIMIT 5")
                result = self.database.query(query)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())

                # Get column types
                cols_info = inspect(self.database.engine).get_columns(table_name)
                col_types = {col["name"]: str(col["type"]) for col in cols_info}

                if df.empty:
                    ui.label("No rows found").classes('text-red-500')
                else:
                    with ui.column().classes("w-full"):
                        ui.label('Table Preview').classes('text-orange-500 text-lg mt-3 ml-3 font-bold')
                        df.columns = [f"{col} ({col_types.get(col, '?')})" for col in df.columns]
                        ui.aggrid.from_pandas(df)

            with ui.row().classes("items-center w-full"):
                with ui.card().classes("items-center bg-[#5898d4]"):
                    ui.label("Table Selection").classes("font-bold text-white")

                    self.table_select = ui.select(
                        options=self.database.db_table_names(),
                        on_change=lambda e: preview_table_display.refresh(e.value)
                    ).props('dense outlined input-class="pl-3"').classes('w-[160px] bg-blue-50 rounded border border-blue-300')

                with ui.column().classes("items-center"):
                    self.sql_input = ui.textarea(
                        placeholder='Type your SQL Query here.',
                    ).props(
                        'dense outlined input-class="pl-2 pt-2"'
                    ).classes("w-[60vh] bg-gray-50 border border-gray-300 rounded resize-none")

                ui.button('Execute').on('click', lambda: self._handle_sql_searches())

            ui.separator()

            with ui.card().tight().classes("w-full bg-gray-50"):
                preview_table_display("")

            # Solr Search
            ui.label('Free Form Search').classes('text-orange-500 text-xl mt-3 ml-3 font-bold')
            self.freeform_text_input = ui.textarea(
                placeholder='Type your search here!',
            ).props(
                'dense outlined input-class="pl-2 pt-2"'
            ).classes("w-[60vh] ml-3 bg-gray-50 border border-gray-300 rounded resize-none")
            ui.button('Execute').on('click', lambda: self._handle_freeform_search()).classes("ml-3")

    async def advanced_search(self):
        with navbar.header():
            ui.page_title("Advanced Search")

            # Name search
            ui.label('Name Search').classes('text-orange-500 ml-3 mt-4 text-xl font-bold')

            self.name_input = ui.input(
                label='Search Names',
                placeholder='e.g.: John Smith, \"John Andrew Smith\"'
            ).on('keydown.enter', self._handle_name_search).classes('w-80 items-center ml-3 mb-4')

            ui.label("You can search full names, first names or just the last name." +
                     "To search for an exact name you can use double quotes (\" \").").classes("ml-3 -mt-4 text-xs italic")

            ui.label("Time Interval").classes("ml-3 mt-2 font-bold")

            with ui.row().classes("ml-3 -mt-5"):
                with ui.input('From') as self.from_date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(on_change=menu.close).props("default-year-month=1600/01/01").bind_value(self.from_date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.from_date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

                with ui.input('To') as self.to_date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(on_change=menu.close).props("default-year-month=1700/12/31").bind_value(self.to_date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.to_date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

            ui.label("Can be YYYY, YYYY-mm or YYYY-mm-dd (e.g. 1643, 1532-10-21)").classes("ml-3 -mt-2 text-xs italic")

            ui.button('Search Names').on('click', self._handle_name_search).classes("items-center mt-4 ml-3")
            ui.separator()

            # Attributes
            ui.label('Attribute Search').classes('text-orange-500 ml-3 mt-4 text-xl font-bold')
            ui.label(
                "You can search up to six attributes. Use the % wildcard to search for any value."
            ).classes("ml-3 mt-2 text-xs italic")

            attr_df = timelink_web_utils.load_data("attributes", self.database)

            self.attr_list = [None] * 6
            self.attr_values = [None] * 6

            for i in range(6):
                with ui.row().classes("ml-3 -mt-2"):
                    self.attr_select = ui.select(
                        options=attr_df["the_type"].unique().tolist(),
                        on_change=lambda new_val, index=i: self._attr_index_list_update(index, new_val.value)
                    ).props('dense outlined input-class="pl-3"').classes('w-[300px] bg-blue-50 rounded border border-blue-300')

                    ui.input(
                        on_change=lambda new_val, index=i: self._attr_value_list_update(index, new_val.value)
                    ).props('outlined dense').classes('w-[200px]')

            with ui.row().classes("ml-3 -mt-2"):
                with ui.input('From') as self.attr_from_date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(on_change=menu.close).props("default-year-month=1600/01/01").bind_value(self.attr_from_date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.attr_from_date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

                with ui.input('To') as self.attr_to_date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(on_change=menu.close).props("default-year-month=1700/12/31").bind_value(self.attr_to_date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.attr_to_date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

            ui.label("Can be YYYY, YYYY-mm or YYYY-mm-dd (e.g. 1643, 1532-10-21)").classes("ml-3 -mt-2 text-xs italic")

            ui.button('Search Attributes').on('click', self._handle_attr_search).classes("items-center mt-4 ml-3")
            ui.separator()

            # Search by ID
            ui.label('ID Search').classes('text-orange-500 ml-3 mt-4 text-xl font-bold')

            with ui.row().classes("ml-3"):
                self.text_input = ui.input(
                    label='Search by ID',
                    placeholder='ID of something (person, source, act, etc..)'
                ).on('keydown.enter', self._handle_id_search).classes('w-80 items-center mb-4')

                ui.button('Search IDs').on('click', self._handle_id_search).classes("items-center mt-4 ml-3 mb-4")

    def _handle_searches(self):
        """Processes the keyword search results."""
        if self.text_input.value:
            keywords = self.text_input.value.replace(' ', '_').rstrip('_')
            ui.navigate.to(f'/search_tables?keywords={keywords}&tables={self.selector.value}')
        else:
            ui.notify("You need a valid input to search the database.")

    async def _handle_sql_searches(self):
        """Handles the search using SQL."""
        if self.sql_input.value:
            app.storage.tab['sql_table'] = self.table_select.value
            app.storage.tab['sql_query'] = self.sql_input.value
            ui.navigate.to('/search_tables_sql')
        else:
            ui.notify("You need a valid SQL string to search the database.")

    async def _handle_freeform_search(self):
        """Processes the keyword search results."""
        if self.freeform_text_input.value:
            ui.notify(f"Searching for this: {self.freeform_text_input.value}")
            results = self.solr_manager.solr_client.search(q=f"content:{self.freeform_text_input.value}")

            print(f"Found {len(results)} document(s).")
            print("-" * 20)

            for result in results:
                print(f"ID: {result.get('id')}")
                print(f"Title: {result.get('title')}")
                print(f"Content: {result.get('content')[:70]}...")
                print("-" * 20)
        else:
            ui.notify("You need to input something before searching.")

    def _handle_id_search(self):
        """Handles the search by ID function."""
        if self.text_input.value:
            ui.navigate.to(f'/id/{self.text_input.value}')
        else:
            ui.notify("You need a valid input to search the database.")

    async def _handle_name_search(self):
        """Handles advanced name searching."""

        if not self.name_input.value:
            ui.notify("You need to type a name to search.")
            return

        query = self.name_input.value.strip()

        # Date parsing
        parsed_from = format_timelink_date(self.from_date.value) or "0001-01-01"
        parsed_to = format_timelink_date(self.to_date.value) or "9999-12-31"

        if parsed_to < parsed_from:
            parsed_from, parsed_to = parsed_to, parsed_from

        # Name parsing
        exact_match = False
        names = []

        if query.startswith('"') and query.endswith('"'):
            exact_match = True
            names = query.replace('"', "")
            names = names.replace(' ', '_').rstrip('_')
        else:
            names = query.replace(' ', '_').rstrip('_')

        ui.navigate.to(f'/search_names?names={names}&from_={parsed_from}&to_={parsed_to}&exact={int(exact_match)}')

    def _attr_index_list_update(self, list_index, new_value):
        """Update attribute list index with the correct value."""

        self.attr_list[list_index] = new_value

    def _attr_value_list_update(self, list_index, new_value):
        """Update attribute list value with the correct input."""

        self.attr_values[list_index] = new_value

    async def _handle_attr_search(self):
        """Handles advanced attribute searching."""

        # Date parsing
        parsed_from = format_timelink_date(self.attr_from_date.value) or "0001-01-01"
        parsed_to = format_timelink_date(self.attr_to_date.value) or "9999-12-31"

        if parsed_to < parsed_from:
            parsed_from, parsed_to = parsed_to, parsed_from

        ui.notify("Will search for:")

        for i in range(len(self.attr_list)):
            if self.attr_list[i] and {self.attr_values[i]}:
                ui.notify(f"{self.attr_list[i]} = {self.attr_values[i]}")

        ui.notify(f"Between {parsed_from} and {parsed_to}.")
