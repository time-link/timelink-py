from timelink.web.pages import navbar
from nicegui import ui, events, app
import pandas as pd
from sqlalchemy import select, func, and_, text
import asyncio
from timelink.api.models import Entity, Person
from timelink.web.models import Activity
import re
from timelink.web import timelink_web_utils
from datetime import datetime


class TablesPage:

    """Pages to display tables"""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver
        self.show_desc = False

    def register(self):
        @ui.page('/tables/persons')
        def display_persons_page(value: str, type: str = None):
            with navbar.header():
                if type:
                    ui.page_title(f"Search for {value} = {type}")
                    self._find_persons(value, type)
                else:
                    ui.page_title(f"Search for {value}")
                    self._display_names(value)

        @ui.page('/tables/relations')
        def display_relations_page(type: str, value: str | None = None, id: str | None = None, is_from: bool | None = True):
            with navbar.header():
                ui.page_title(f"Relations of Type {type.title()}")
                self._display_relations_view(type, value, id, is_from)

        @ui.page('/tables/functions')
        def display_functions_page(type: str):
            with navbar.header():
                ui.page_title(f"Functions of Type {type.title()}")
                self._display_functions_view(type)

        @ui.page('/tables/attributes')
        def display_attr_page(attr_type: str, attr_value: str | None = None):
            with navbar.header():
                ui.page_title(f"Attributes of Type {attr_type.title()}")
                self._display_entity_with_attributes(attr_type, attr_value)

        @ui.page('/tables/geoentities')
        def display_geo_page(name: str):
            with navbar.header():
                ui.page_title("Geoentity Table")
                self._display_geoentities(name)

        @ui.page('/tables/acts')
        def display_act_page(name: str):
            with navbar.header():
                ui.page_title("Acts Table")
                self._display_acts(name)

        @ui.page('/all_tables/{table_name}')
        def display_tables_page(table_name: str, display_type: str, value: str):
            with navbar.header():
                ui.page_title(f"{table_name.title()} Display")
                self._display_tables(table_name, display_type, value)

        @ui.page('/search_tables')
        async def search_database_page(keywords: str, tables: str):
            with navbar.header():
                ui.page_title("Search Results")
                keyword_list = keywords.split("_")
                await self._search_database(keyword_list, tables)

        @ui.page('/search_names')
        async def search_database_page_names(names: str, from_: str = None, to_: str = None, exact: str = "0"):
            with navbar.header():
                ui.page_title("Name Search Results")

                exact_match = str(exact).lower() in ("1", "true", "yes")

                names_to_query = names.split("_")

                await self._name_search_database(names_to_query, from_, to_, exact_match)

        @ui.page('/search_tables_sql')
        async def search_database_sql_page():
            with navbar.header():
                ui.page_title("SQL Search Results")

                await ui.context.client.connected()
                sql_table = app.storage.tab.get('sql_table')
                sql = app.storage.tab.get('sql_query')

                if sql:
                    app.storage.tab['sql_query'] = None
                    app.storage.tab['sql_table'] = None
                    await self._display_sql_results(sql, sql_table)
                else:
                    ui.label(
                        'Could not load SQL query results - did you try to directly access this link directly the browser?'
                    ).classes('text-xl text-red-500 font-semibold ml-1')

    def _display_names(self, name_to_query: str):
        """
        Display all results with the passed name.

        Args:
            name_to_query    : Name to lookup on the database.
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>
                    ''')
        try:

            table = self.database.get_table("persons")
            sql_stmt = select(table).where(table.c.name.like(name_to_query))

            with self.database.session() as session:
                retrieved_df = pd.DataFrame(session.execute(sql_stmt))
                retrieved_df = timelink_web_utils.add_description_column(
                    df=retrieved_df,
                    database=self.database,
                    id_column="id",
                    session=session
                )

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

                grid.on('cellClicked', lambda e: ui.navigate.to(f'/id/{e.args["data"]["id"]}') if e.args["colId"] == "id" else None)

            else:
                ui.label('No entries found.').classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label('Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
            print(e)

    def _display_tables(self, table_to_retrieve: str, table_type: str, info_to_display: str):

        """
        Queries the database for information on different tables and displays them after.
        The table and information retrieved depend on where the user clicked on the web app.
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>
                    ''')

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

                    names_grid.on(
                        'cellClicked',
                        lambda e:
                        self._redirect_to_view(e, e.args["data"]["name"], "persons")
                        if e.args["colId"] == "name_count" else None
                    )

                else:
                    ui.label('No names found.').classes('text-grey-500 font-semibold ml-1')

            except Exception as e:
                ui.label(
                    f'Could not load details for selected letter {info_to_display}.'
                ).classes('text-red-500 font-semibold ml-1')
                print(e)

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
                            {'headerName': f'{table_to_retrieve.title()} Count',
                                'field': 'attribute_count',
                                'cellClass': 'highlight-cell'}
                        ],
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': table_pd.to_dict("records"),
                    }).classes('h-[70vh]')

                    stat_grid.on(
                        'cellClicked',
                        lambda e:
                        self._redirect_to_view(e, info_to_display, table_to_retrieve)
                        if e.args["colId"] == "attribute_count" else None
                    )

                else:
                    ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

            except Exception as e:
                ui.label(
                    f'Could not load details for selected attribute {info_to_display}.'
                ).classes('text-red-500 font-semibold mt-4')
                print(e)

        elif table_type == "sources":

            ui.markdown('##### **Sources in Database**').classes('mb-4 text-orange-500')

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
                            {'headerName': 'OBS', 'field': 'obs', 'wrapText': True, 'autoHeight': True},
                        ],
                        "pagination": True,
                        "paginationPageSize": 50,
                        "paginationPageSizeSelector": [10, 30, 50, 100],
                        'rowData': table_pd.to_dict("records"),
                    }).classes('h-[70vh]').on(
                        'cellClicked',
                        lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None
                    )
                    table_ag.on('firstDataRendered', lambda: table_ag.run_grid_method('autoSizeAllColumns'))

                else:
                    ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

            except Exception as e:
                ui.label(
                    f'Could not load details for selected attribute {info_to_display}.'
                ).classes('text-red-500 font-semibold mt-4')
                print(e)

    def _find_persons(self, attr_type: str, attr_value: str):
        """Find and display a person with specificed attribute type and value."""

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>''')

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
                }).classes('h-[70vh]').on(
                    'cellClicked',
                    lambda e:
                    ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None
                )

            else:
                ui.label(
                    f'No persons with attribute type \"{attr_type}\" and value \"{attr_value}\" combination found.'
                ).classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label(
                'Could not load details for selected attribute type/value combination.'
            ).classes('text-red-500 font-semibold mt-4')
            print(e)

    def _display_relations_view(
        self,
        rel_type: str,
        rel_value: str | None = None,
        rel_id: str | None = None,
        is_from: bool | None = True
    ):
        """
        Display table of relations given a relation type and value, with a specific id if provided.

        Args:
            rel_type   : The type of relation to display.
            rel_value   : The value of the relation, if applicable.
            rel_id      : The name of the person with this relationship type and value.
            is_from     : Flag that specifies if we are querying the destinationn or the origin
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>''')

        if not rel_id:
            if rel_value:
                ui.markdown(f'##### **Entries with relation of type {rel_type} = {rel_value}**').classes('mb-4 text-orange-500')

            else:
                ui.markdown(f'##### **Entries with relation of type {rel_type}**').classes('mb-4 text-orange-500')

            try:
                nrels = self.database.views["nrelations"]

                base_stmt = select(
                    nrels.c.origin_id,
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
                    cols = [
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

                    table.on(
                        'cellClicked',
                        lambda e:
                        ui.navigate.to(f"/id/{e.args["data"]["origin_id"]}") if e.args["colId"] == "origin_name"
                        else ui.navigate.to(f"/id/{e.args["data"]["destination_id"]}") if e.args["colId"] == "destination_name"
                        else ui.navigate.to(f"/id/{e.args["data"]["relation_id"]}") if e.args["colId"] == "relation_type"
                        else None
                    )

                else:
                    ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {rel_type}.').classes('text-red-500 font-semibold mt-4')
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
                        persons_table.join(
                            nrels,
                            persons_table.c.id == nrels.c.origin_id
                        ).join(persons_table_2, nrels.c.destination_id == persons_table_2.c.id)
                    )
                    .where(
                        and_(
                            (persons_table.c.name if is_from else persons_table_2.c.name) == rel_id,
                            nrels.c.relation_type == rel_type,
                            nrels.c.relation_value == rel_value
                        )
                    ).order_by(persons_table.c.name, persons_table_2.c.name, nrels.c.relation_date)
                )

                with self.database.session() as session:
                    rels_of_type = session.execute(stmt)
                    rels_of_type_df = pd.DataFrame(rels_of_type)

                if not rels_of_type_df.empty:

                    rels_of_type_df = timelink_web_utils.add_description_column(
                        df=rels_of_type_df,
                        database=self.database,
                        id_column="id_1",
                        session=session
                    )

                    cols = [
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

                    table.on(
                        'cellClicked',
                        lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id"
                        else ui.navigate.to(f"/id/{e.args["data"]["id_1"]}") if e.args["colId"] == "id_1"
                        else ui.navigate.to(f"/id/{e.args["data"]["relation_id"]}") if e.args["colId"] == "relation_type"
                        else None
                    )

                else:
                    ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

            except Exception as e:
                ui.label(f'Could not load details for selected attribute {rel_type}.').classes('text-red-500 font-semibold mt-4')
                print(e)

    def _display_entity_with_attributes(self, attr_type: str, attr_value: str | None = None):
        """
        Display all entities with given attribute. If a value is passed, the entities displayed
        are filtered to attributes with that value.

        Args:
            attr_type   : The type of the attribute to display.
            attr_value  : The specific value of the attribute (optional).
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>''')

        with ui.row().classes('w-full justify-between items-center'):

            nattributes = self.database.get_view('nattributes')
            stmt = ""

            if attr_value:
                ui.markdown(f'##### **Entries with attribute {attr_type} = {attr_value}**').classes('mb-4 text-orange-500')
                stmt = select(
                    nattributes.c.id,
                    nattributes.c.name,
                    nattributes.c.the_type,
                    nattributes.c.the_date,
                    nattributes.c.sex,
                    nattributes.c.the_value.label(attr_type.title()),
                    nattributes.c.pobs
                ).where(
                    and_(
                        nattributes.c.the_type.like(attr_type),
                        nattributes.c.the_value.like(attr_value)
                    ))
            else:
                ui.markdown(f'##### **Entries with attribute {attr_type}**').classes('mb-4 text-orange-500')

                stmt = select(
                    nattributes.c.id,
                    nattributes.c.name,
                    nattributes.c.the_type,
                    nattributes.c.the_date,
                    nattributes.c.sex,
                    nattributes.c.the_value.label(attr_type.title()),
                    nattributes.c.pobs
                ).where(nattributes.c.the_type.like(attr_type))

            ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

        try:

            with self.database.session() as session:
                with_attribute = session.execute(stmt)
                table_pd = pd.DataFrame(with_attribute)

            if not table_pd.empty:
                # Pre-process dataframe so we can display it as an aggrid
                with self.database.session() as session:
                    table_pd = timelink_web_utils.add_description_column(
                        df=table_pd,
                        database=self.database,
                        id_column="id",
                        session=session
                    )

                processed_pd, cols = timelink_web_utils.pre_process_attributes_df(df_to_process=table_pd, attr_type=attr_type)

                grid = ui.aggrid({
                    'columnDefs': cols,
                    "pagination": True,
                    "paginationPageSize": 50,
                    "paginationPageSizeSelector": [10, 30, 50, 100],
                    'rowData': processed_pd.to_dict("records"),
                }).classes('h-[75vh] w-full')

                grid.on('firstDataRendered', lambda: self._fit_columns(grid))
                grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None)

            else:
                ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label(f'Could not load details for selected attribute {attr_type}.').classes('text-red-500 font-semibold mt-4')
            print(e)

    def _display_functions_view(self, func_type: str):
        """
        Display view of functions.

        Args:
            func_type   : The type of function to display.
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>''')

        ui.markdown(f'##### **Entities with function of type {func_type}**').classes('mb-4 text-orange-500')

        try:
            nfunctions = self.database.views["nfunctions"]

            stmt = select(
                nfunctions.c.id,
                nfunctions.c.name,
                nfunctions.c.func,
                nfunctions.c.act_date
            ).where(nfunctions.c.func == func_type).order_by(nfunctions.c.name)

            with self.database.session() as session:
                funcs_of_type = session.execute(stmt)
                funcs_of_type_df = pd.DataFrame(funcs_of_type)

            if not funcs_of_type_df.empty:

                cols = [
                    {'headerName': 'ID', 'field': 'id', 'cellClass' : 'highlight-cell'},
                    {'headerName': 'Name', 'field': 'name'},
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

                table.on(
                    'cellClicked',
                    lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None
                )

            else:
                ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label(f'Could not load details for selected attribute {func_type}.').classes('text-red-500 font-semibold mt-4')
            print(e)

    def _display_geoentities(self, geoentity: str):
        """
        Display all results with the passed geoentity.

        Args:
            geoentity    : Name to lookup on the database.
        """

        ui.add_body_html('''<style>
                        .highlight-cell { text-decoration: underline dotted; }
                        .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                        </style>''')

        try:

            table = self.database.get_table("geoentity")
            sql_stmt = select(table).where(table.c.name.like(geoentity))

            with self.database.session() as session:
                retrieved_df = pd.DataFrame(session.execute(sql_stmt))
                retrieved_df = timelink_web_utils.add_description_column(
                    df=retrieved_df,
                    database=self.database,
                    id_column="id",
                    session=session
                )

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

                grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None)

            else:
                ui.label('No entries found.').classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label('Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
            print(e)

    def _display_acts(self, act_type: str):
        """
        List all acts with given type.

        Args:
            act_type   : The type of the act to display.
        """

        ui.add_body_html('''<style>
                .highlight-cell { text-decoration: underline dotted; }
                .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                </style>''')

        with ui.row().classes('w-full justify-between items-center'):

            ui.markdown(f'##### **Acts with type {act_type}**').classes('mb-4 text-orange-500')
            ui.button('Toggle Description', on_click=lambda: self._toggle_description(grid))

        try:

            act_table = self.database.get_table('acts')
            stmt = select(
                act_table.c.id,
                act_table.c.the_type,
                act_table.c.the_date,
                act_table.c.loc,
                act_table.c.ref,
                act_table.c.obs
            ).where(act_table.c.the_type == act_type)

            with self.database.session() as session:
                acts = session.execute(stmt)
                acts_df = pd.DataFrame(acts)

            if not acts_df.empty:

                with self.database.session() as session:
                    acts_df = timelink_web_utils.add_description_column(
                        df=acts_df,
                        database=self.database,
                        id_column="id",
                        session=session
                    )

                processed_pd, cols = timelink_web_utils.pre_process_attributes_df(df_to_process=acts_df, attr_type="  ")

                grid = ui.aggrid({
                    'columnDefs': cols,
                    "pagination": True,
                    "paginationPageSize": 50,
                    "paginationPageSizeSelector": [10, 30, 50, 100],
                    'rowData': processed_pd.to_dict("records"),
                }).classes('h-[75vh] w-full')

                grid.on('firstDataRendered', lambda: self._fit_columns(grid))
                grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None)

            else:
                ui.label('No data found.').classes('text-grey-500 font-semibold ml-1')

        except Exception as e:
            ui.label(f'Could not load details for selected act type {act_type}.').classes('text-red-500 font-semibold mt-4')
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
            ui.navigate.to(f'/tables/attributes?attr_type={type}&attr_value={e.args["data"]["the_value"]}')

        elif table == "persons":  # Names view
            ui.navigate.to(f'/tables/persons?value={type}')

        else:  # Relation table views
            ui.navigate.to(f'/tables/relations?type={type}&value={e.args["data"]["the_value"]}')

    async def _search_database(self, keywords, tables):
        """ Search database for a variable number of terms and display the results on a table.

            Args:

                keywords   : list of keywords to be searched for.
                tables     : the tables within which to search
                from_date  : the date from which results start
                to_date    : the date up to which the results will be looked for
                exact      : if the query needs to be an exact match or not.
        """

        ui.add_body_html('''<style>
                .highlight-cell { text-decoration: underline dotted; }
                .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                </style>''')

        terms = [t.lower() for t in keywords]

        tables_map = {
            "All Entities" : {"rperson", "person", "act"},
            "Real Persons" : {"rperson"},
            "Persons" : {"person"},
            "Acts" : {"act"},
        }

        def run_query():
            result_list = []
            with self.database.session() as session:
                results = session.execute(select(Entity)).scalars().all()
                for entity in results:
                    if entity.pom_class not in tables_map[tables]:
                        continue
                    searchable_text = str(entity).lower()
                    words = set(re.findall(r"\b\w+\b", searchable_text))
                    if all(term in words for term in terms):
                        result_list.append({
                            "entity": entity.id,
                            "entity_class": entity.pom_class,
                            "description": str(entity)
                        })

                if result_list:
                    session.add(Activity(
                        entity_id=" ".join(terms),
                        entity_type=tables,
                        activity_type='searched',
                        desc=f'Found {len(result_list)} results with this search.'
                    ))
                    session.commit()

            return result_list

        result_list = await asyncio.to_thread(run_query)

        results_df = pd.DataFrame(result_list, columns=["entity", "entity_class", "description"])

        expected_cols = [
            {'headerName': 'ID', 'field': 'entity', 'cellClass': 'highlight-cell'},
            {'headerName': 'Entity Type', 'field': 'entity_class'},
            {'headerName': 'Description', 'field': 'description'},
        ]

        grid = ui.aggrid({
            'columnDefs': expected_cols,
            "pagination": True,
            "paginationPageSize": 50,
            "paginationPageSizeSelector": [50, 100, 200],
            'rowData': results_df.to_dict("records")}
        ).classes('h-[70vh]')

        grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["entity"]}") if e.args["colId"] == "entity" else None)

    async def _display_sql_results(self, sql_query: str, sql_table: str):
        """ Search database using a custom SQL query.

            Args:

                sql_query   : The query to be executed.
                sql_table   : Table where the query was executed on.
        """

        ui.add_body_html('''<style>
                .highlight-cell { text-decoration: underline dotted; }
                .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                </style>''')

        ui.label("SQL Query Results").classes('text-orange-500 text-xl mt-4 font-bold')

        ui.label(sql_query).classes('text-sm italic mt-3 text-gray-600')

        results = self.database.query(text(sql_query))
        results_df = pd.DataFrame(results.fetchall(), columns=results.keys())

        if results_df.empty:
            ui.label("No rows found").classes('text-red-500')
        else:
            with self.database.session() as session:
                session.add(Activity(
                    entity_id=sql_query,
                    entity_type=sql_table,
                    activity_type='SQL search',
                    desc=f'Found {results_df.shape[0]} results with this search.'
                ))
                session.commit()

            with ui.card().tight().classes("w-full bg-gray-50"):

                col_defs = timelink_web_utils.build_expected_col_list(results_df, "id")

                grid = ui.aggrid({
                    'columnDefs': col_defs,
                    "pagination": True,
                    "paginationPageSize": 50,
                    "paginationPageSizeSelector": [50, 100, 200],
                    'rowData': results_df.to_dict("records")}
                ).classes('h-[70vh]')

                grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" else None)

    async def _name_search_database(self, names, from_date, to_date, exact):
        """ Search persons table for specific people.

            Args:

                names      : list of keywords to be searched for.
                from_date  : the date from which results start
                to_date    : the date up to which the results will be looked for
                exact      : if the query needs to be an exact match or not.
        """

        ui.add_body_html('''<style>
            .highlight-cell { text-decoration: underline dotted; }
            .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
            </style>''')

        names_to_find = [n.lower() for n in names]

        def run_query():
            result_list = []
            with self.database.session() as session:
                results = session.execute(select(Person)).scalars().all()
                for entity in results:

                    searchable_text = str(entity.name).lower()

                    if exact:
                        search_string = " ".join(names_to_find).lower().strip()
                        match_find = search_string == searchable_text

                    else:
                        words = set(re.findall(r"\b\w+\b", searchable_text))
                        match_find = all(any(name.lower() in word.lower() for word in words) for name in names_to_find)

                    if match_find:

                        dated_bio = entity.dated_bio()

                        min_person_date = min(dated_bio.keys())
                        min_person_datetime = timelink_web_utils.format_date(min_person_date)

                        if (
                            datetime.strptime(from_date, "%Y-%m-%d") <=
                            datetime.strptime(min_person_datetime, "%Y-%m-%d") <=
                            datetime.strptime(to_date, "%Y-%m-%d")
                        ):

                            function_value = "N/A"

                            for _, val in dated_bio.items():
                                for rel in val:
                                    if getattr(rel, "the_type", None) == "function-in-act":
                                        function_value = getattr(rel, "the_value", None)

                            result_list.append({
                                "name": entity.name.title(),
                                "sex": entity.sex,
                                "obs": entity.obs,
                                "id" : entity.id,
                                "function" : function_value
                            })

                if result_list:

                    search_type_string = "Name search (exact)" if exact else "Name search"

                    session.add(Activity(
                        entity_id=" ".join(names),
                        entity_type="Persons",
                        activity_type=search_type_string,
                        desc=f'Between {from_date} and {to_date} - Found {len(result_list)} results.'
                    ))
                    session.commit()

            return result_list

        result_list = await asyncio.to_thread(run_query)

        results_df = pd.DataFrame(result_list, columns=["name", "function", "sex", "obs", "id"])

        expected_cols = [
            {'headerName': 'Name', 'field': 'name', 'cellClass': 'highlight-cell'},
            {'headerName': 'Function', 'field': 'function'},
            {'headerName': 'Sex', 'field': 'sex'},
            {'headerName': 'Observations', 'field': 'obs'},
        ]

        grid = ui.aggrid({
            'columnDefs': expected_cols,
            "pagination": True,
            "paginationPageSize": 50,
            "paginationPageSizeSelector": [50, 100, 200],
            'rowData': results_df.to_dict("records")}
        ).classes('h-[70vh]')

        grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "name" else None)

    def _toggle_description(self, grid):
        """Toggle description button functionality to properly resize the table."""

        self.show_desc = not self.show_desc
        grid.run_grid_method('setColumnVisible', 'description', self.show_desc)

        self._fit_columns(grid)

    def _fit_columns(self, grid):
        grid.run_grid_method('autoSizeAllColumns')
        grid.run_grid_method('sizeColumnsToFit')
