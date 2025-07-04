from nicegui import ui, events
import pandas as pd
import string
from sqlalchemy import select, func, and_
from timelink.pandas import entities_with_attribute
from timelink.api.schemas import EntityAttrRelSchema


class ExploreTab:
    """
    Encapsulate the logic of the Explore Tab.
    """

    def __init__(self, database_obj, timelink_utils_obj, kserver_obj):
        """
        Initializes the ExploreTab.

        Args:
            database_obj: The database object
            timelink_utils_obj: An object containing Timelink web utility functions.
            kserver_obj: The Kleio server object for status checks.
        """
        self.database = database_obj
        self.timelink_web_utils = timelink_utils_obj
        self.kserver = kserver_obj

        # UI components that need to be accessed by methods
        self.search_column = None
        self.details_column = None
        self.text_input = None
        self.attribute_type_search = None
        self.attribute_value_search = None
        self.show_desc = False

    def create_ui(self):
        """
        Creates the NiceGUI UI elements for the Explore tab.
        """
        self.search_column = ui.column().classes('w-full')
        self.details_column = ui.column().classes('w-full')
        self.details_column.visible = False

        # Landing page for Database Exploration.
        with self.search_column:

            # Search by ID
            ui.label('Search by ID').classes('text-orange-500 text-xl font-bold')

            with ui.row():
                self.text_input = ui.input(label='Explore Database', placeholder='ID of something (person, source, act, etc..)').classes('w-80 items-center mb-4')
                search_button = ui.button('Search').classes("items-center mt-4 ml-3 mb-4")

            # Search by Name
            ui.label('Names').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                for letter in string.ascii_uppercase + '?':
                    ui.label(letter)\
                        .on('click', lambda _, clicked_letter=letter: self._display_info(clicked_letter, "names", "persons"))\
                        .tooltip(f"Show all names started with {letter}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

            # Search by Attributes
            ui.label('Attributes').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                attr_df = self.timelink_web_utils.load_data("attributes", self.database)
                if attr_df is not None and not attr_df.empty:
                    grouped = attr_df.groupby("the_type")["count"].sum().to_dict()
                    for result in attr_df["the_type"].unique():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(result).on('click', lambda _, clicked_attr=result: self._display_info(clicked_attr, "statistics", "attributes"))\
                                .tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                            ui.label(str(grouped.get(result, 0))).on('click', lambda _, clicked_attr_count=result: self._display_entity_with_attributes(attr_type=clicked_attr_count))\
                                .tooltip(f"Show all results with {result}").classes('-mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Search by Functions
            ui.label('Functions').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                func_df = self.timelink_web_utils.load_data("functions", self.database)
                if func_df is not None and not func_df.empty:
                    grouped = func_df.groupby("the_value")["count"].sum().to_dict()
                    for result in func_df["the_value"].tolist():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(result).on('click', lambda _, clicked_func=result: self._display_functions_view(clicked_func))\
                                .tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                            ui.label(str(grouped.get(result, 0))).classes('-mt-10 text-xs text-blue-500 font-semibold')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Search by Relations
            ui.label('Relations').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                rel_df = self.timelink_web_utils.load_data("relations", self.database)
                if rel_df is not None and not rel_df.empty:
                    grouped = rel_df.groupby("the_type")["count"].sum().to_dict()
                    for result in rel_df["the_type"].tolist():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(result).on('click', lambda _, clicked_rel=result: self._display_info(clicked_rel, "statistics", "relations"))\
                                .tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                            ui.label(str(grouped.get(result, 0))).on('click', lambda _, clicked_rel_count=result: self._display_relations_view(rel_type=clicked_rel_count))\
                                .tooltip(f"Show all results with {result}").classes('-mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Advanced Search by attribute type and value.
            ui.label('Advanced Options').classes('text-orange-500 text-xl font-bold')
            with ui.row():
                self.attribute_type_search = ui.input(label='Choose Attribute Type', placeholder='Write an attribute type here...').classes('w-80 items-center mb-4 mr-3')
                self.attribute_value_search = ui.input(label='Choose Attribute Value', placeholder='Write an attribute value here...').classes('w-80 items-center mb-4 mr-3')
                advanced_options_button = ui.button('Show Persons').classes("items-center mt-4 ml-3 mb-4")

            # Show database sources.
            ui.label("Show Sources").on('click', lambda x: self._display_info(x, "sources", "sources")).classes('mb-4 cursor-pointer text-orange-500 text-xl underline')

            # Update functionality of text searches.
            search_button.on('click', self._handle_id_search)
            self.text_input.on('keydown.enter', self._handle_id_search)

            self.attribute_type_search.on('keydown.enter', self._handle_advanced_search)
            self.attribute_value_search.on('keydown.enter', self._handle_advanced_search)
            advanced_options_button.on('click', self._handle_advanced_search)

    def _handle_id_search(self):
        """Handles the search by ID function."""
        if self.text_input.value:
            self._load_entity_details(self.text_input.value, " ")
        else:
            ui.notify("You need a valid input to search the database.")

    def _handle_advanced_search(self):
        """Handles the advanced search by attribute type and value."""
        if self.attribute_type_search.value and self.attribute_value_search.value:
            self._find_persons(self.attribute_type_search.value, self.attribute_value_search.value)
        else:
            ui.notify("You need both attribute type and value to search!")

    def _back_to_explore_cleanup(self):
        """Handle returning from displayed table details to the main explore page"""
        self.details_column.visible = False
        self.search_column.visible = True
        self.show_desc = False
        ui.run_javascript("window.scrollTo(0,0);")
        if self.text_input:
            self.text_input.value = ''

    def _detail_column_cleanup(self):
        """Handle information display when switching pages on the explore page."""
        self.search_column.visible = False
        self.details_column.clear()
        self.details_column.visible = True
        self.show_desc = False
        ui.run_javascript("window.scrollTo(0,0);")


    def _toggle_description(self, grid):
        """Toggle description button functionality to properly resize the table."""
        
        self.show_desc = not self.show_desc
        grid.run_grid_method('setColumnVisible', 'description', self.show_desc)

        if self.show_desc:
            grid.run_grid_method('autoSizeAllColumns')
        else:
            grid.run_grid_method('sizeColumnsToFit')

    def _display_info(self, info_to_display: str, table_type: str, table_to_retrieve: str = None):

        """
        Queries the database for information on different tables and displays them after.
        The table and information retrieved depend on where the user clicked on the web app.
        """

        self._detail_column_cleanup()

        with self.details_column:

            # To query names table for available names starting with X letter
            if table_type == "names":
                ui.markdown(f'#### **All names started with {info_to_display}**').classes('mb-4 text-orange-500')

                try:
                    person_table = self.database.get_table(table_to_retrieve)

                    stmt = (
                        select(person_table.c.name, func.count().label("name_count"))
                        .where(person_table.c.name.like(f"{info_to_display}%"))
                        .group_by(person_table.c.name)
                        .order_by(func.count().desc())
                    )

                    with self.database.session() as session:
                        names_results = session.execute(stmt)
                        names_df = pd.DataFrame(names_results)

                    if not names_df.empty:

                        names_grid = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Name', 'field': 'name'},
                                {'headerName': 'Name Count', 'field': 'name_count', 'cellClass': 'highlight-cell'}
                            ],
                            "pagination": True,
                            "paginationPageSize": 50,
                            "paginationPageSizeSelector": [10, 30, 50, 100],
                            'rowData': names_df.to_dict("records"),
                        }).classes('h-[70vh]')


                        names_grid.on('cellClicked', lambda e: self._redirect_to_view(e, e.args["data"]["name"], "persons") if e.args["colId"] == "name_count" else None)

                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                    else:
                        ui.label(f'No names found.').classes('text-grey-500 font-semibold ml-1')
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                except Exception as e:
                    ui.label(f'Could not load details for selected letter {info_to_display}.').classes('text-red-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                    print(e)

            # For attributes found inside other tables.
            elif table_type == "statistics":

                ui.markdown(f'#### **Statistics for {info_to_display}**').classes('mb-4 text-orange-500')

                try:
                    table = self.database.get_table(table_to_retrieve)

                    stmt = (
                        select(table.c.the_value, func.count().label("attribute_count"))
                        .where(table.c.the_type.like(f"{info_to_display}"))
                        .group_by(table.c.the_value)
                        .order_by(func.count().desc())
                    )

                    with self.database.session() as session:
                        table_results = session.execute(stmt)
                        table_pd = pd.DataFrame(table_results)

                    if not table_pd.empty:

                        stat_grid = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Value', 'field': 'the_value'},
                                {'headerName': f'{table_to_retrieve.title()} Count', 'field': 'attribute_count', 'cellClass': 'highlight-cell'}
                            ],
                            "pagination": True,
                            "paginationPageSize": 50,
                            "paginationPageSizeSelector": [10, 30, 50, 100],
                            'rowData': table_pd.to_dict("records"),
                        }).classes('h-[70vh]')

                        stat_grid.on('cellClicked', lambda e: self._redirect_to_view(e, info_to_display, table_to_retrieve) if e.args["colId"] == "attribute_count" else None)

                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                    else:
                        ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                except Exception as e:
                    ui.label(f'Could not load details for selected attribute {info_to_display}.').classes('text-red-500 font-semibold mt-4')
                    print(e)
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            # For "Show Sources" button
            elif table_type == "sources":

                ui.markdown(f'#### **Sources in Database**').classes('mb-4 text-orange-500')

                try:
                    table = self.database.get_table(table_to_retrieve)

                    stmt = select(table).order_by(table.c.the_type, table.c.the_date)

                    with self.database.session() as session:
                        table_results = session.execute(stmt)
                        table_pd = pd.DataFrame(table_results)

                    if not table_pd.empty:


                        table_ag = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                                {'headerName': 'THE_TYPE', 'field': 'the_type'},
                                {'headerName': 'THE_DATE', 'field': 'the_date'},
                                {'headerName': 'LOC', 'field': 'loc'},
                                {'headerName': 'REF', 'field': 'ref'},
                                {'headerName': 'KLEIOFILE', 'field': 'kleiofile'},
                                {'headerName': 'REPLACES', 'field': 'replace'},
                                {'headerName': 'OBS', 'field': 'obs', 'wrapText':True, 'autoHeight': True},
                            ],
                            "pagination": True,
                            "paginationPageSize": 50,
                            "paginationPageSizeSelector": [10, 30, 50, 100],
                            'rowData': table_pd.to_dict("records"),
                        }).classes('h-[70vh]').on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"], " ") if e.args["colId"] == "id" else None)
                        table_ag.on('firstDataRendered', lambda: table_ag.run_grid_method('autoSizeAllColumns'))
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                    else:
                        ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                except Exception as e:
                    ui.label(f'Could not load details for selected attribute {info_to_display}.').classes('text-red-500 font-semibold mt-4')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                    print(e)

    def _find_persons(self, attr_type: str, attr_value: str):
        """Find and display a person with specificed attribute type and value."""

        self._detail_column_cleanup()

        with self.details_column:
            try:
                persons = self.database.get_table("persons")
                attributes = self.database.get_table("attributes")

                stmt = (
                    select(persons.c.id, persons.c.name, attributes.c.the_date)
                    .where(
                        and_(
                            attributes.c.the_type.like(attr_type),
                            attributes.c.the_value.like(attr_value),
                            attributes.c.entity == persons.c.id,
                        )
                    ).order_by(persons.c.name, attributes.c.the_date))

                with self.database.session() as session:
                    found_table = session.execute(stmt)
                    table_pd = pd.DataFrame(found_table)

                if table_pd is not None and not table_pd.empty:
                    ui.label(f'List of persons with {attr_type} = {attr_value}').classes('mb-4 text-lg font-bold text-orange-500')


                    ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                            {'headerName': 'Name', 'field': 'name'},
                            {'headerName': 'Date', 'field': 'the_date'},
                        ],
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': table_pd.to_dict("records"),
                    }).classes('h-[70vh]').on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"],  " ") if e.args["colId"] == "id" else None)
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No persons with attribute type \"{attr_type}\" and value \"{attr_value}\" combination found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute type/value combination.').classes('text-red-500 font-semibold mt-4')
                print(e)
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

    def _load_entity_details(self, item_id: str, title: str = None):
        "Page to load details on a specific entity."

        self._detail_column_cleanup()

        with self.details_column:
            try:

                with self.database.session() as session:
                    entity = self.database.get_entity(item_id, session=session)
                    entity_kleio = entity.to_kleio()
                    entity_mr = EntityAttrRelSchema.model_validate(entity)
                    class_dict = entity_mr.model_dump(exclude=['contains'])
                    
                with ui.row():
                    ui.label(title).on('click', lambda: self._display_names(title)).classes('cursor-pointer underline decoration-dotted text-xl font-bold')
                    ui.label(f"id: {item_id}").classes('text-xl font-bold text-orange-500')
                
                with ui.row().classes('items-center gap-1'):
                     ui.label('groupname:').classes('text-orange-500')
                     ui.label(f'{class_dict["groupname"]}').classes('mr-3 text-blue-400')
                     ui.label('sex:').classes('text-orange-500')
                     ui.label("???").classes('mr-3 text-blue-400')
                     ui.label('line:').classes('text-orange-500')
                     ui.label(f'{class_dict["the_line"]}').classes('mr-3 text-blue-400')


                ui.label("Person Info").classes('font-bold text-lg')
                with ui.row().classes('w-full'):
                    expected_cols = [
                            {'headerName': 'Year', 'field': 'year'},
                            {'headerName': 'Function', 'field': 'function'},
                            {'headerName': 'Attributes', 'field': 'attr', 'wrapText': True, 'autoHeight': True, 'word-break': 'break-word'},
                            {'headerName': 'Relations', 'field': 'rels'},
                            {'headerName': 'Name', 'field': 'name'},
                            ]

                    ui.aggrid({
                        'columnDefs': expected_cols,
                        'rowData': [{"year" : "test1", "function" : "test2", "attr" : entity_kleio, "rels" : "test4", "name" : "test5"}],
                    }).classes('h-[70vh]')

            except Exception as e:
                ui.label(f'Could not load details for selected id {item_id}').classes('text-red-500 font-semibold')
                print(e)

            ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup)

    
    def _display_entity_with_attributes(self, attr_type: str, attr_value: str | None = None):
        """
        Display all entities with given attribute. If a value is passed, the entities displayed are filtered to attributes with that value.

        Args:
            attr_type   : The type of the attribute to display.
            attr_value  : The specific value of the attribute (optional).
        """
        self._detail_column_cleanup()

        with self.details_column:
            
            with ui.row().classes('w-full justify-between items-center'):
                
                if attr_value:
                    ui.markdown(f'#### **Entries with attribute {attr_type} = {attr_value}**').classes('mb-4 text-orange-500')
                else:
                    ui.markdown(f'#### **Entries with attribute {attr_type}**').classes('mb-4 text-orange-500')
                
                ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))
            
            try:
                table_pd = entities_with_attribute(the_type=attr_type, the_value=attr_value, sql_echo=True, db=self.database).reset_index()

                if not table_pd.empty:
                    # Pre-process dataframe so we can display it as an aggrid
                    with self.database.session() as session:
                        table_pd = self.timelink_web_utils.add_description_column(df=table_pd, database=self.database, session=session)

                    processed_pd, cols = self.timelink_web_utils.pre_process_attributes_df(df_to_process=table_pd, attr_type=attr_type)


                    grid = ui.aggrid({
                        'columnDefs': cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': processed_pd.to_dict("records"),
                    }).classes('h-[70vh]')

                    grid.on('firstDataRendered', lambda: grid.run_grid_method('sizeColumnsToFit'))
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"], " ") if e.args["colId"] == "id" else None)

                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {attr_type}.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)


    def _display_relations_view(self, rel_type: str, rel_value: str | None = None):
        """
        Display table of relations given a relation type and value.

        Args:
            rel_type   : The type of relation to display.
            rel_type   : The value of the relation, if applicable.
        """
        
        self._detail_column_cleanup()

        with self.details_column:

            if rel_value:
                ui.markdown(f'#### **Entries with relation of type {rel_type} = {rel_value}**').classes('mb-4 text-orange-500')
            
            else:
                ui.markdown(f'#### **Entries with relation of type {rel_type}**').classes('mb-4 text-orange-500')

            try:
                nrels = self.database.views["nrelations"]

                base_stmt = select(nrels.c.origin_id,
                            nrels.c.origin_name,
                            nrels.c.relation_type,
                            nrels.c.relation_value,
                            nrels.c.destination_id,
                            nrels.c.destination_name,
                            nrels.c.relation_date
                            )
                
                stmt = base_stmt.where(nrels.c.relation_type == rel_type)

                if rel_value:
                    stmt = stmt.where(nrels.c.relation_value == rel_value)

                with self.database.session() as session:
                    rels_of_type = session.execute(stmt)
                    rels_of_type_df = pd.DataFrame(rels_of_type)

                if not rels_of_type_df.empty:
                    # Pre-process dataframe so we can display it as an aggrid
                    cols =  [
                            {'headerName': 'ID A', 'field': 'origin_id', 'hide': True},
                            {'headerName': 'Name A', 'field': 'origin_name', 'cellClass' : 'highlight-cell'},
                            {'headerName': 'Relation Type', 'field': 'relation_type'},
                            {'headerName': 'Value', 'field': 'relation_value'},
                            {'headerName': 'Name B', 'field': 'destination_name', 'cellClass' : 'highlight-cell'},
                        ]

                    table = ui.aggrid({
                        'columnDefs': cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': rels_of_type_df.to_dict("records"),
                    }).classes('h-[70vh]')

                    table.on('cellClicked', lambda e: 
                             self._load_entity_details(e.args["data"]["origin_id"],  " ") if e.args["colId"] == "origin_name" 
                             else (
                                 self._load_entity_details(e.args["data"]["destination_id"], " ") if e.args["colId"] == "destination_name" else None
                             ))

                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {rel_type}.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)


    def _display_functions_view(self, func_type: str):
        """
        Display view of functions.

        Args:
            func_type   : The type of function to display.
        """
        
        self._detail_column_cleanup()

        with self.details_column:

            ui.markdown(f'#### **Entities with function of type {func_type}**').classes('mb-4 text-orange-500')

            try:
                nfunctions = self.database.views["nfunctions"]

                stmt = select(nfunctions.c.id,
                            nfunctions.c.name,
                            nfunctions.c.func,
                            nfunctions.c.act_date
                            ).where(nfunctions.c.func == func_type).order_by(nfunctions.c.name)
                

                with self.database.session() as session:
                    funcs_of_type = session.execute(stmt)
                    funcs_of_type_df = pd.DataFrame(funcs_of_type)

                if not funcs_of_type_df.empty:

                    # Pre-process dataframe so we can display it as an aggrid
                    cols =  [
                            {'headerName': 'ID', 'field': 'id', 'cellClass' : 'highlight-cell'},
                            {'headerName': 'Name', 'field': 'name',},
                            {'headerName': 'Function', 'field': 'func'},
                            {'headerName': 'Act Date', 'field': 'act_date'},
                        ]

                    table = ui.aggrid({
                        'columnDefs': cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': funcs_of_type_df.to_dict("records"),
                    }).classes('h-[70vh]')

                    table.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"], " ") if e.args["colId"] == "id"  else None)

                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {func_type}.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)


    def _display_names(self, name_to_query: str):
        """
        Display all results with the passed name.

        Args:
            name_to_query    : Name to lookup on the database.
        """
        
        self._detail_column_cleanup()

        with self.details_column:
            
            try:
                
                table = self.database.get_table("persons")
                sql_stmt = select(table).where(table.c.name.like(name_to_query))

                with self.database.session() as session:
                    retrieved_df = pd.DataFrame(session.execute(sql_stmt))
                    retrieved_df = self.timelink_web_utils.add_description_column(df=retrieved_df, database=self.database, session=session)

                if not retrieved_df.empty:

                    with ui.row().classes('w-full justify-between items-center'):
                        ui.markdown(f'#### **All entries with {name_to_query}**').classes('mb-4 text-orange-500')
                        ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

                    expected_cols = [
                            {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                            {'headerName': 'Name', 'field': 'name'},
                            {'headerName': 'Sex', 'field': 'sex'},
                            {'headerName': 'Observations', 'field': 'obs'},
                            {'headerName': 'Description', 'field': 'description', 'hide': True, 'wrapText': True, 'autoHeight': True, 'word-break': 'break-word'},
                            ]

                    grid = ui.aggrid({
                        'columnDefs': expected_cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [50, 100, 200],
                        'rowData': retrieved_df.to_dict("records")}
                    ).classes('h-[70vh]')
                    
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"], e.args["data"]["name"]) if e.args["colId"] == "id" else None)

                    with ui.row():
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No entries found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
                print(e)


    def _redirect_to_view(self, e: events.GenericEventArguments, type: str, table: str):
        """
        Function to map generic functions to a specific view of a table according to the values that were clicked.

        Args:
            e       : Event argument dictionary that contains information on the clicked cell.
            type    : The type of value that is to be displayed (eg: activa)
            table   : The table that is to be queried.

        """

        if table == "attributes":  # Attribute table views
            self._display_entity_with_attributes(attr_type=type, attr_value=e.args["data"]["the_value"])


        elif table == "persons":    # Names view
            self._display_names(name_to_query= type)

        else:  # Relation table views
            self._display_relations_view(rel_type=type, rel_value=e.args["data"]["the_value"])