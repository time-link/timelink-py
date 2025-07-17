from nicegui import ui, events
import pandas as pd
import string
from sqlalchemy import select, func, and_
from timelink.pandas import entities_with_attribute
from timelink.api.models import Entity
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
        self.relations = ["eclesiástica", "geografica", "institucional", "parentesco", "profissional", "sociabilidade", "identification"]

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
                        .on('click', lambda _, clicked_letter=letter: self._display_tables(clicked_letter, "names", "persons"))\
                        .tooltip(f"Show all names started with {letter}").classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

            # Search by Attributes
            ui.label('Attributes').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                attr_df = self.timelink_web_utils.load_data("attributes", self.database)
                if attr_df is not None and not attr_df.empty:
                    grouped = attr_df.groupby("the_type")["count"].sum().to_dict()
                    for result in attr_df["the_type"].unique():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(result).on('click', lambda _, clicked_attr=result: self._display_tables(clicked_attr, "statistics", "attributes"))\
                                .tooltip(f"Show all the values with {result}").classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                            ui.label(str(grouped.get(result, 0))).on('click', lambda _, clicked_attr_count=result: self._display_entity_with_attributes(attr_type=clicked_attr_count))\
                                .tooltip(f"Show all results with {result}").classes('highlight-cell -mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
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
                                .tooltip(f"Show all the values with {result}").classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
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
                            ui.label(result).on('click', lambda _, clicked_rel=result: self._display_tables(clicked_rel, "statistics", "relations"))\
                                .tooltip(f"Show all the values with {result}").classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                            ui.label(str(grouped.get(result, 0))).on('click', lambda _, clicked_rel_count=result: self._display_relations_view(rel_type=clicked_rel_count))\
                                .tooltip(f"Show all results with {result}").classes('highlight-cell -mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Advanced Search by attribute type and value.
            ui.label('Advanced Options').classes('text-orange-500 text-xl font-bold')
            with ui.row():
                self.attribute_type_search = ui.input(label='Choose Attribute Type', placeholder='Write an attribute type here...').classes('w-80 items-center mb-4 mr-3')
                self.attribute_value_search = ui.input(label='Choose Attribute Value', placeholder='Write an attribute value here...').classes('w-80 items-center mb-4 mr-3')
                advanced_options_button = ui.button('Show Persons').classes("items-center mt-4 ml-3 mb-4")

            # Show database sources.
            ui.label("Show Sources").on('click', lambda x: self._display_tables(x, "sources", "sources")).classes('mb-4 cursor-pointer text-orange-500 text-xl underline')

            # Update functionality of text searches.
            search_button.on('click', self._handle_id_search)
            self.text_input.on('keydown.enter', self._handle_id_search)

            self.attribute_type_search.on('keydown.enter', self._handle_advanced_search)
            self.attribute_value_search.on('keydown.enter', self._handle_advanced_search)
            advanced_options_button.on('click', self._handle_advanced_search)

    def _handle_id_search(self):
        """Handles the search by ID function."""
        if self.text_input.value:
            self._load_entity_details(self.text_input.value)
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

        self._fit_columns(grid)


    def _fit_columns(self, grid):
        grid.run_grid_method('autoSizeAllColumns')
        grid.run_grid_method('sizeColumnsToFit')
        

    def _display_tables(self, info_to_display: str, table_type: str, table_to_retrieve: str = None):

        """
        Queries the database for information on different tables and displays them after.
        The table and information retrieved depend on where the user clicked on the web app.
        """

        self._detail_column_cleanup()

        with self.details_column:

            # To query names table for available names starting with X letter
            if table_type == "names":
                ui.markdown(f'##### **All names started with {info_to_display}**').classes('mb-4 text-orange-500')

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

                ui.markdown(f'##### **Statistics for {info_to_display}**').classes('mb-4 text-orange-500')

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

                ui.markdown(f'##### **Sources in Database**').classes('mb-4 text-orange-500')

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
                        }).classes('h-[70vh]').on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)
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
                    }).classes('h-[70vh]').on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No persons with attribute type \"{attr_type}\" and value \"{attr_value}\" combination found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute type/value combination.').classes('text-red-500 font-semibold mt-4')
                print(e)
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
        

    def _load_entity_details(self, item_id: str):
        "Maps to the correct loading function for a specific entity."

        self._detail_column_cleanup()

        display_func_map = {
            "person": self._display_person,
            "geoentity": self._display_geoentity,
            "act": self._display_act,
            "source": self._display_act,
            "relation": self._display_act
        }

        with self.details_column:
            try:
                with self.database.session() as session:
                    entity = self.database.get_entity(item_id, session=session)
                    if entity:
                        display_func = display_func_map.get(entity.pom_class)
                        if display_func:
                            display_func(entity)
                        else:
                            ui.label(f"No page created for {entity.pom_class} yet.").classes('mb-4 text-lg font-bold text-red-500')
                            ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                    else:
                        ui.label(f"No entity with value {item_id} found.").classes('mb-4 text-lg font-bold text-red-500')
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                

            except Exception as e:
                ui.label(f'Could not load details for selected entity.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)

    def _display_person(self, entity: Entity):
        "Page to load details on an entity of type person."

        self._detail_column_cleanup()

        with self.details_column:

            with ui.row():
                ui.label(entity.name).on('click', lambda: self._display_names(entity.name)).classes('cursor-pointer underline decoration-dotted text-xl font-bold')
                ui.label(f"id: {entity.id}").classes('text-xl font-bold text-orange-500')
            
            with ui.row().classes('items-center gap-1'):
                    ui.label('groupname:').classes('text-orange-500')
                    ui.label(entity.groupname).classes('mr-3 text-blue-400')
                    ui.label('sex:').classes('text-orange-500')
                    ui.label(entity.sex).classes('mr-3 text-blue-400')
                    ui.label('line:').classes('text-orange-500')
                    ui.label(entity.the_line).classes('mr-3 text-blue-400')

            parsed_attributes, parsed_relations_in, parsed_relations_out = self.timelink_web_utils.parse_entity_details(entity)
            
            with ui.card().tight().classes("w-full"):
                with ui.tabs() as tabs:
                    person_info_tab = ui.tab('p_info', label='Person Info').classes("w-full bg-blue-100 text-orange-500 font-bold")
                with ui.tab_panels(tabs, value=person_info_tab).classes('w-full'):
                    with ui.tab_panel(person_info_tab).classes("items-center"):
                        with ui.grid(columns=9).classes("w-full bg-blue-100 text-orange-500 font-bold"):
                            ui.label("Year").classes("text-center")
                            ui.label("Function").classes("text-center")
                            ui.label("Attributes").classes("break-all col-span-4 text-center")
                            ui.label("Relations").classes("text-center col-span-2 text-center")
                            ui.label("Name").classes("text-center")
                        
                        with ui.grid(columns=9).classes("w-full items-start gap-4 text-xs"):
                            ui.label("-").classes("ml-1 mt-1 mb-1")     #TODO: YEAR DETAILS - WHEN IS THE YEAR HERE AND WHEN IS IT IN ATTR?
                            with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                for function in parsed_relations_out:
                                    if function["the_type"] not in self.relations:
                                        with ui.row().classes("no-wrap"):
                                            ui.label(f'{function["dest_name"]} : {function["the_value"]}').on(
                                                "click", lambda _, id=function["destination"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')

                            with ui.column().classes("col-span-4 ml-1 mt-1 mb-1 items-righ"):
                                for date, pairs in parsed_attributes.items():
                                    with ui.row().classes("items-start mr-1 no-wrap"):
                                        ui.label(date).classes("font-bold text-blue-500")
                                        with ui.column():
                                            for pair in pairs:
                                                for key, value in pair.items():
                                                    if key == "obs":
                                                        continue
                                                    obs = pair.get("obs", "")
                                                    with ui.row().classes("no-wrap"):
                                                        ui.label(key).on(
                                                            "click", lambda _, k=key: self._display_tables(k, "statistics", "attributes")).classes('highlight-cell cursor-pointer decoration-dotted')
                                                        ui.label(":")
                                                        ui.label(value).on(
                                                            "click", lambda _, k=key, v=value: self._find_persons(attr_type=k, attr_value=v)).classes('highlight-cell cursor-pointer decoration-dotted')
                                                        if obs:
                                                            ui.label(obs)
                                                ui.separator()
                            with ui.column().classes("col-span-2 ml-1 mt-1 mb-1"):
                                    for rel in parsed_relations_in:
                                        with ui.row().classes("no-wrap"):
                                            ui.label("tem como")
                                            ui.label(rel["the_value"]).on(
                                                "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["org_name"]: self._display_relations_view(type, value, id, True)
                                                ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                            ui.label(" : ")
                                            ui.label(rel["org_name"]).on(
                                                "click", lambda _, id=rel["origin"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted')
                                    for rel in parsed_relations_out:
                                        if rel["the_type"] in self.relations:
                                            with ui.row().classes("no-wrap"):
                                                ui.label(rel["the_value"]).on(
                                                    "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["dest_name"]: self._display_relations_view(type, value, id, False)
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                ui.label("de:").classes('-ml-3')
                                                ui.label(rel["dest_name"]).on(
                                                    "click", lambda _, id=rel["destination"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')

                            ui.label(entity.name)

        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup)


    def _display_geoentity(self, entity: Entity):
        "Page to load details on an entity of type person."

        self._detail_column_cleanup()

        with self.details_column:

            with ui.row():
                ui.label(entity.name).on('click', lambda: self._display_geoentities(entity.name)).classes('cursor-pointer underline decoration-dotted text-xl font-bold')
            
            with ui.row().classes('items-center gap-1'):
                    ui.label('id:').classes('text-orange-500')
                    ui.label(entity.id).classes('mr-3 text-blue-400')
                    ui.label('inside:').classes('text-orange-500')
                    ui.label(entity.inside).on('click', lambda: self._load_entity_details(entity.inside)).classes('mr-3 cursor-pointer underline decoration-dotted')
                    ui.label('Full file:').classes('text-orange-500')


            parsed_attributes, parsed_relations_in, parsed_relations_out = self.timelink_web_utils.parse_entity_details(entity)
            
            with ui.card().tight().classes("w-full"):
                with ui.tabs() as tabs:
                    geo_info_tab = ui.tab('p_info', label='Geoentity Details').classes("w-full bg-blue-100 text-orange-500 font-bold")
                with ui.tab_panels(tabs, value=geo_info_tab).classes('w-full'):
                    with ui.tab_panel(geo_info_tab).classes("items-center"):
                        with ui.grid(columns=8).classes("w-full bg-blue-100 text-orange-500 font-bold"):
                            ui.label("Year").classes("text-center")
                            ui.label("Name").classes("text-center")
                            ui.label("Geometry").classes("text-center")
                            ui.label("Functions").classes("text-center")
                            ui.label("Attributes").classes("text-center col-span-2")
                            ui.label("Relations").classes("text-center col-span-2")

                        with ui.grid(columns=8).classes("w-full items-start gap-4 text-xs"):
                            ui.label("-").classes("ml-1 mt-1 mb-1")  
                            ui.label(entity.name).classes("ml-1 mt-1 mb-1")
                            ui.label(" ").classes("ml-1 mt-1 mb-1")  #TODO: GEOMETRY DETAILS
                            with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                for function in parsed_relations_out:
                                    if function["the_type"] not in self.relations:
                                        with ui.row().classes("no-wrap"):
                                            ui.label(f'{function["dest_name"]} : {function["the_value"]}').on(
                                                "click", lambda _, id=function["destination"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')

                            with ui.column().classes("col-span-2 ml-1 mt-1 mb-1 items-righ"):
                                for _, pairs in parsed_attributes.items():
                                    with ui.row().classes("items-start mr-1 no-wrap"):
                                        with ui.column():
                                            for pair in pairs:
                                                for key, value in pair.items():
                                                    if key == "obs":
                                                        continue
                                                    obs = pair.get("obs", "")
                                                    with ui.row().classes("no-wrap"):
                                                        ui.label(key).classes('font-bold')
                                                        ui.label(":")
                                                        ui.label(value)
                                                        if obs:
                                                            ui.label(obs)
                            with ui.column().classes("col-span-2 ml-1 mt-1 mb-1"):
                                    for rel in parsed_relations_in:
                                        with self.database.session() as session:
                                            original_entity = self.database.get_entity(rel["origin"], session=session)
                                            with ui.row().classes("no-wrap"):
                                                ui.label("tem como")
                                                ui.label(rel["the_value"]).on(
                                                    "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["org_name"]: self._display_relations_view(type, value, id, True)
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                                ui.label(" : ")
                                                ui.label(original_entity.name).on(
                                                    "click", lambda _, id=rel["origin"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted')
                                    for rel in parsed_relations_out:
                                        if rel["the_type"] in self.relations:
                                            with self.database.session() as session:
                                                original_entity = self.database.get_entity(rel["origin"], session=session)
                                                with ui.row().classes("no-wrap"):
                                                    ui.label(rel["the_value"]).on(
                                                        "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["dest_name"]: self._display_relations_view(type, value, id, False)
                                                        ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                    ui.label("de").classes('-ml-3')
                                                    ui.label(original_entity.name).on(
                                                        "click", lambda _, id=rel["origin"]: self._load_entity_details(id)).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')


            ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup)
    
    def _render_act_entity(self, entity, level=0):
        "Helper function to print act lines"

        indent = f"ml-{level * 4}"
        act_dict = EntityAttrRelSchema.model_validate(entity).model_dump(exclude=['rels_in'])
        obs = ""

        with ui.row():
            if not act_dict['groupname'] == "relation":
                
                ui.label(f"{act_dict['groupname']}$").classes(f"font-bold {indent}")

                if act_dict['groupname'] not in {"n", "pai", "mae", "pad", "mad", "mrmad"}: # If its the act's header
                    
                    ui.label(act_dict['id']).classes(f"-ml-3")

                    for extra_info_key, extra_info_value in act_dict["extra_info"].items():
                        if extra_info_key not in {'class'}:
                            value = getattr(entity, extra_info_key)
                            kleio_class = extra_info_value.get('kleio_element_class')
                            if kleio_class == "obs":
                                obs = f"{value}{extra_info_value.get('comment', '')}"
                            else:
                                ui.label(f"/{kleio_class}=").classes(f'-ml-4 text-green-800')
                                if kleio_class in {'inside', 'id'}:
                                    ui.label(value).on(
                                        "click", lambda _, id=value: self._load_entity_details(id)
                                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-4')
                                else:
                                    ui.label(value).classes(f'-ml-4')

                    ui.label("/inside=").classes(f'-ml-4')
                    ui.label(entity.inside).on(
                        "click", lambda: self._load_entity_details(entity.inside)
                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-4') if entity.inside else ui.label("root").classes(f"-ml-4")
                
                else: # If not, we only need the name, sex and id
                    ui.label(getattr(entity, 'name')).on(
                                        lambda _, id=getattr(entity, 'id'): self._load_entity_details(id)
                                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-3')
                    ui.label(f"/sex={getattr(entity, 'sex')}").classes(f"-ml-3 text-green-800")
                    ui.label(f"/id=").classes(f"-ml-3 text-green-800")
                    ui.label(getattr(entity, 'id')).on(
                                        "click", lambda _, id=getattr(entity, 'id'): self._load_entity_details(id)
                                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-3')
        if obs:
            ui.label(f"/obs={obs}").classes(f"font-mono italic text-sm")

        # TODO - This is slow, needs a better option - commenting for now.
        """
        for contained_element in act_dict.get("contains", []):
            with self.database.session() as session:
                new_entity = self.database.get_entity(contained_element['id'], session=session)
                self._render_act_entity(new_entity, level + 1)
        """


    def _display_act(self, entity: Entity):
        "Page to load details on an entity of type act."

        self._detail_column_cleanup()

        with self.details_column:

            with ui.row():
                ui.label(entity.the_type)\
                    .on('click', lambda: self._list_acts(act_type=entity.the_type))\
                        .classes('cursor-pointer underline decoration-dotted text-xl font-bold')

            self._render_act_entity(entity, level=0)  #TODO - ASYNC

            ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup)
    
    
    def _list_acts(self, act_type: str):
        """
        List all acts with given type.

        Args:
            act_type   : The type of the act to display.
        """

        self._detail_column_cleanup()

        with self.details_column:
            
            with ui.row().classes('w-full justify-between items-center'):
                
                ui.markdown(f'##### **Acts with type {act_type}**').classes('mb-4 text-orange-500')
                ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

            try:
                
                act_table = self.database.get_table('acts')
                stmt = select(act_table.c.id,
                                act_table.c.the_type,
                                act_table.c.the_date,
                                act_table.c.loc,
                                act_table.c.ref,
                                act_table.c.obs
                                ).where(
                                    act_table.c.the_type == act_type)

                with self.database.session() as session:
                    acts = session.execute(stmt)
                    acts_df = pd.DataFrame(acts)

                if not acts_df.empty:
                    
                    with self.database.session() as session:
                        acts_df = self.timelink_web_utils.add_description_column(df=acts_df, database=self.database, id_column="id", session=session)

                    processed_pd, cols = self.timelink_web_utils.pre_process_attributes_df(df_to_process=acts_df, attr_type="  ")

                    grid = ui.aggrid({
                        'columnDefs': cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': processed_pd.to_dict("records"),
                    }).classes('h-[75vh] w-full')

                    grid.on('firstDataRendered', lambda: self._fit_columns(grid))
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)

                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected act type {act_type}.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)


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
                    ui.markdown(f'##### **Entries with attribute {attr_type} = {attr_value}**').classes('mb-4 text-orange-500')
                else:
                    ui.markdown(f'##### **Entries with attribute {attr_type}**').classes('mb-4 text-orange-500')
                
                ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

            try:
                table_pd = entities_with_attribute(the_type=attr_type, the_value=attr_value, sql_echo=True, db=self.database).reset_index()

                if not table_pd.empty:
                    # Pre-process dataframe so we can display it as an aggrid
                    with self.database.session() as session:
                        table_pd = self.timelink_web_utils.add_description_column(df=table_pd, database=self.database, id_column="id", session=session)

                    processed_pd, cols = self.timelink_web_utils.pre_process_attributes_df(df_to_process=table_pd, attr_type=attr_type)

                    grid = ui.aggrid({
                        'columnDefs': cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': processed_pd.to_dict("records"),
                    }).classes('h-[75vh] w-full')

                    grid.on('firstDataRendered', lambda: self._fit_columns(grid))
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)

                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {attr_type}.').classes('text-red-500 font-semibold mt-4')
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                print(e)


    def _display_relations_view(self, rel_type: str, rel_value: str | None = None, rel_id: str | None = None, is_from: bool | None = True):
        """
        Display table of relations given a relation type and value, with a specific id if provided.

        Args:
            rel_type   : The type of relation to display.
            rel_value   : The value of the relation, if applicable.
            rel_id      : The name of the person with this relationship type and value.
            is_from     : Flag that specifies if we are querying the destinationn or the origin
        """
        
        self._detail_column_cleanup()

        with self.details_column:

            if not rel_id:
                if rel_value:
                    ui.markdown(f'##### **Entries with relation of type {rel_type} = {rel_value}**').classes('mb-4 text-orange-500')
                
                else:
                    ui.markdown(f'##### **Entries with relation of type {rel_type}**').classes('mb-4 text-orange-500')

                try:
                    nrels = self.database.views["nrelations"]

                    base_stmt = select(nrels.c.origin_id,
                                nrels.c.origin_name,
                                nrels.c.relation_type,
                                nrels.c.relation_value,
                                nrels.c.destination_id,
                                nrels.c.relation_id,
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
                                {'headerName': 'Relation Type', 'field': 'relation_type', 'cellClass' : 'highlight-cell'},
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
                                self._load_entity_details(e.args["data"]["origin_id"]) if e.args["colId"] == "origin_name"
                                else self._load_entity_details(e.args["data"]["destination_id"]) if e.args["colId"] == "destination_name"
                                else self._load_entity_details(e.args["data"]["relation_id"]) if e.args["colId"] == "relation_type"
                                else None
                        )

                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                    else:
                        ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                except Exception as e:
                    ui.label(f'Could not load details for selected attribute {rel_type}.').classes('text-red-500 font-semibold mt-4')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')
                    print(e)

            else: 

                with ui.row().classes('w-full justify-between items-center'):
                    ui.markdown(f'##### **Entries with relation {rel_type}/{rel_value} = {rel_id}**').classes('mb-4 text-orange-500')
                    ui.button('Toggle Description', on_click=lambda: self._toggle_description(table))
                
                try:
                    
                    persons_table = self.database.get_table('persons')
                    persons_table_2 = persons_table.alias("p2")
                    nrels = self.database.views["nrelations"]

                    stmt = (
                            select(
                                persons_table.c.id,
                                persons_table.c.name,
                                nrels.c.relation_type,
                                nrels.c.relation_value,
                                persons_table_2.c.id,
                                persons_table_2.c.name,
                                nrels.c.relation_date,
                            )
                            .select_from(
                                persons_table.join(nrels, persons_table.c.id == nrels.c.origin_id)
                                    .join(persons_table_2, nrels.c.destination_id == persons_table_2.c.id)
                            )
                            .where(
                                and_(
                                    (persons_table.c.name if is_from else persons_table_2.c.name) == rel_id,
                                    nrels.c.relation_type == rel_type,
                                    nrels.c.relation_value == rel_value
                                )
                            )
                            .order_by(persons_table.c.name, persons_table_2.c.name, nrels.c.relation_date)
                        )
                    

                    with self.database.session() as session:
                        rels_of_type = session.execute(stmt)
                        rels_of_type_df = pd.DataFrame(rels_of_type)

                    if not rels_of_type_df.empty:
                        rels_of_type_df = self.timelink_web_utils.add_description_column(df=rels_of_type_df, database=self.database, id_column="id_1", session=session)

                        cols =  [
                                {'headerName': 'ID A', 'field': 'id', 'cellClass' : 'highlight-cell'},
                                {'headerName': 'Name A', 'field': 'name'},
                                {'headerName': 'Relation Type', 'field': 'relation_type'},
                                {'headerName': 'Value', 'field': 'relation_value'},
                                {'headerName': 'ID B', 'field': 'id_1', 'cellClass' : 'highlight-cell'},
                                {'headerName': 'Name B', 'field': 'name_1'},
                                {'headerName': 'Relation Date', 'field': 'relation_date'},
                                {'headerName': 'Description', 'field': 'description', 'wrapText': True, 'hide': True, 'minWidth': 300},
                            ]

                        table = ui.aggrid({
                            'columnDefs': cols,
                            "pagination": True,
                            "paginationPageSize": 50,
                            "paginationPageSizeSelector": [10, 30, 50, 100],
                            'rowData': rels_of_type_df.to_dict("records"),
                        }).classes('h-[70vh]')

                        table.on('cellClicked', lambda e: 
                                self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id"
                                else self._load_entity_details(e.args["data"]["id_1"]) if e.args["colId"] == "id_1"
                                else self._load_entity_details(e.args["data"]["relation_id"]) if e.args["colId"] == "relation_type"
                                else None
                        )

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

            ui.markdown(f'##### **Entities with function of type {func_type}**').classes('mb-4 text-orange-500')

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

                    table.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id"  else None)

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
                    retrieved_df = self.timelink_web_utils.add_description_column(df=retrieved_df, database=self.database, id_column="id", session=session)

                if not retrieved_df.empty:

                    with ui.row().classes('w-full justify-between items-center'):
                        ui.markdown(f'##### **All entries with {name_to_query}**').classes('mb-4 text-orange-500')
                        ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

                    expected_cols = [
                            {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                            {'headerName': 'Name', 'field': 'name'},
                            {'headerName': 'Sex', 'field': 'sex'},
                            {'headerName': 'Observations', 'field': 'obs'},
                            {'headerName': 'Description', 'field': 'description', 'hide': True, 'wrapText': True, 'autoHeight': True},
                            ]

                    grid = ui.aggrid({
                        'columnDefs': expected_cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [50, 100, 200],
                        'rowData': retrieved_df.to_dict("records")}
                    ).classes('h-[70vh]')
                    
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)

                    with ui.row():
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No entries found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
                print(e)
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')


    def _display_geoentities(self, geoentity: str):
        """
        Display all results with the passed geoentity.

        Args:
            geoentity    : Name to lookup on the database.
        """
        
        self._detail_column_cleanup()

        with self.details_column:
            
            try:
                
                table = self.database.get_table("geoentity")
                sql_stmt = select(table).where(table.c.name.like(geoentity))

                with self.database.session() as session:
                    retrieved_df = pd.DataFrame(session.execute(sql_stmt))
                    retrieved_df = self.timelink_web_utils.add_description_column(df=retrieved_df, database=self.database, id_column="id", session=session)

                if not retrieved_df.empty:

                    with ui.row().classes('w-full justify-between items-center'):
                        ui.markdown(f'##### **All entries with {geoentity}**').classes('mb-4 text-orange-500')
                        ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

                    expected_cols = [
                            {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                            {'headerName': 'Name', 'field': 'name'},
                            {'headerName': 'Type', 'field': 'the_type'},
                            {'headerName': 'Observations', 'field': 'obs'},
                            {'headerName': 'Description', 'field': 'description', 'hide': True, 'wrapText': True, 'autoHeight': True},
                            ]

                    grid = ui.aggrid({
                        'columnDefs': expected_cols,
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [50, 100, 200],
                        'rowData': retrieved_df.to_dict("records")}
                    ).classes('h-[70vh]')
                    
                    grid.on('cellClicked', lambda e: self._load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)

                    with ui.row():
                        ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

                else:
                    ui.label(f'No entries found.').classes('text-grey-500 font-semibold ml-1')
                    ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

            except Exception as e:
                ui.label(f'Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
                print(e)
                ui.button('Back to Explore Page', on_click=self._back_to_explore_cleanup).classes('mt-2')

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


        elif table == "persons":  # Names view
            self._display_names(name_to_query=type)

        else:  # Relation table views
            self._display_relations_view(rel_type=type, rel_value=e.args["data"]["the_value"])