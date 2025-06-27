from nicegui import ui, app, events
import timelink_web_utils
from sqlalchemy import select, func, and_
import pandas as pd
import sys
from contextlib import contextmanager
import asyncio
import string

port = 8000
kserver = None
database = None

async def initial_setup():
    """Connect to the Kleio Server and load settings found on the .env"""
    global database, kserver
    kserver, database = await timelink_web_utils.run_setup()


@contextmanager
def disable(button: ui.button):
    button.disable()
    try:
        yield
    finally:
        button.enable()


async def update_from_sources(button: ui.button) -> None:
    """ Attempt to update database from sources."""

    with disable(button):
        ui.notify("Updating database from sources...")
        try:
            await asyncio.to_thread(timelink_web_utils.run_imports_sync, database)
            ui.notify("Done updating the database!", type="positive")
        except Exception as e:
            ui.notify(f"ERROR: Database import failed: {e}", type="negative")


@ui.page('/')
def index():

    # Helper functions
    def back_to_explore_cleanup():
        """Handle returning from the details of a person."""
        details_column.visible = False
        search_column.visible = True
        ui.run_javascript("window.scrollTo(0,0);")
        
        if text_input:
            text_input.value = ''

    with ui.header().classes(replace='row items-center'):
        with ui.tabs()as tabs:
            ui.tab('explore', label="Explore")
            ui.tab('faq', label="Status Check")

    with ui.tab_panels(tabs).classes('w-full'):
        with ui.tab_panel('explore'):
            """Explore Page - search_column will be used for an overview of the available data. details_column will be used for information on specific queries."""
            
            # Column definitions
            search_column = ui.column().classes('w-full')
            details_column = ui.column().classes('w-full')
            details_column.visible = False

            def select_from_name(e: events.GenericEventArguments):
                """Display all persons with the passed name."""

                search_column.visible = False
                details_column.clear()
                details_column.visible = True
                ui.run_javascript("window.scrollTo(0,0);")

                with details_column:
                    try:
                        person_table = database.get_table('persons')

                        stmt = (select(person_table).where(person_table.c.name.like(f"{e.args["data"]["name"]}")))

                        with database.session() as session:
                            persons_df = pd.DataFrame(session.execute(stmt))

                        if not persons_df.empty:

                            ui.add_body_html('''
                                <style>
                                .highlight-id { text-decoration: underline; }
                                .highlight-id:hover { color: orange; font-weight: bold; cursor: pointer;}
                                </style>
                                ''')

                            ui.aggrid({
                                'columnDefs': [
                                    {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-id'},
                                    {'headerName': 'Name', 'field': 'name'},
                                    {'headerName': 'Sex', 'field': 'sex'},
                                    {'headerName': 'Observations', 'field': 'obs'}
                                    ],
                                "pagination": True,
                                "paginationPageSize": 10,
                                "paginationPageSizeSelector": [10, 30, 50, 100],
                                'rowData': persons_df.to_dict("records")}
                                ).classes('h-[70vh]').on('cellClicked', lambda e: load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)
                            
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')


                        else:
                            ui.label(f'No entries found.').classes('text-grey-500 font-semibold ml-1')
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                    except Exception as e:
                        ui.label(f'Could not load details for entry.').classes('text-red-500 font-semibold ml-1')
                        print(e)
                        
            def display_info(word: str, type: str, table_to_retrieve: str = None):
                
                """Queries the database for information on different tables and displays them after.
                The table and information retrieved depend on where the user clicked on the web app."""
                
                search_column.visible = False
                details_column.clear()
                details_column.visible = True
                ui.run_javascript("window.scrollTo(0,0);")


                with details_column:
                    
                    # To query names table for available names starting with X letter
                    if type == "letter":
                        ui.markdown(f'#### **All names started with {word}**').classes('mb-4 text-orange-500')

                        try:
                            person_table = database.get_table('persons')

                            stmt = (
                                select(person_table.c.name, func.count().label("name_count"))
                                .where(person_table.c.name.like(f"{word}%"))
                                .group_by(person_table.c.name)
                                .order_by(func.count().desc())
                            )

                            with database.session() as session:
                                names_results = session.execute(stmt)
                                names_df = pd.DataFrame(names_results)

                            if not names_df.empty:

                                ui.add_body_html('''
                                    <style>
                                    .highlight-name-count { text-decoration: underline; }
                                    .highlight-name-count:hover { color: orange; font-weight: bold; cursor: pointer; }
                                    </style>
                                    ''')

                                ui.aggrid({
                                    'columnDefs': [
                                        {'headerName': 'Name', 'field': 'name'},
                                        {'headerName': 'Name Count', 'field': 'name_count', 'cellClass': 'highlight-name-count'}
                                    ],
                                    "pagination": True,
                                    "paginationPageSize": 10,
                                    "paginationPageSizeSelector": [10, 30, 50, 100],
                                    'rowData': names_df.to_dict("records"),
                                }).classes('h-[70vh]').on('cellClicked', lambda e: select_from_name(e) if e.args["colId"] == "name_count" else None)

                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                            else:
                                ui.label(f'No names found.').classes('text-grey-500 font-semibold ml-1')
                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                        except Exception as e:
                            ui.label(f'Could not load details for selected letter {word}.').classes('text-red-500 font-semibold ml-1')
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')
                            print(e)

                    # For attributes found inside other tables.
                    elif type == "statistics":
                        
                        ui.markdown(f'#### **Statistics for {word}**').classes('mb-4 text-orange-500')
                        
                        try:
                            table = database.get_table(table_to_retrieve)

                            stmt = (
                                select(table.c.the_value, func.count().label("attribute_count"))
                                .where(table.c.the_type.like(f"{word}"))
                                .group_by(table.c.the_value)
                                .order_by(table.c.the_value)
                            )

                            with database.session() as session:
                                table_results = session.execute(stmt)
                                table_pd = pd.DataFrame(table_results)

                            if not table_pd.empty:

                                ui.add_body_html('''
                                    <style>
                                    .highlight-cell { text-decoration: underline; }
                                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                                    </style>
                                    ''')

                                ui.aggrid({
                                    'columnDefs': [
                                        {'headerName': 'Value', 'field': 'the_value'},
                                        {'headerName': 'Attribute Count', 'field': 'attribute_count', 'cellClass': 'highlight-cell'}
                                    ],
                                    "pagination": True,
                                    "paginationPageSize": 10,
                                    "paginationPageSizeSelector": [10, 30, 50, 100],
                                    'rowData': table_pd.to_dict("records"),
                                }).classes('h-[70vh]').on('cellClicked', lambda e: ui.notify(f"Attribute {e.args["data"]} was clicked!", type="positive"))

                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                            else:
                                ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                        except Exception as e:
                            ui.label(f'Could not load details for selected attribute {word}.').classes('text-red-500 font-semibold mt-4')
                            print(e)
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')
                    
                    # For "Show Sources" button
                    else:
                        
                        ui.markdown(f'#### **Sources in Database**').classes('mb-4 text-orange-500')
                        
                        try:
                            table = database.get_table(table_to_retrieve)

                            stmt = select(table).order_by(table.c.the_type, table.c.the_date)

                            with database.session() as session:
                                table_results = session.execute(stmt)
                                table_pd = pd.DataFrame(table_results)

                            if not table_pd.empty:
                                    
                                ui.add_body_html('''
                                    <style>
                                    .highlight-cell { text-decoration: underline; }
                                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                                    </style>
                                    ''')

                                table= ui.aggrid({
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
                                    "paginationPageSize": 10,
                                    "paginationPageSizeSelector": [10, 30, 50, 100],
                                    'rowData': table_pd.to_dict("records"),
                                }).classes('h-[70vh]').on('cellClicked', lambda e: load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)  
                                table.on('firstDataRendered', lambda: table.run_grid_method('autoSizeAllColumns'))
                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')
                            else:
                                ui.label(f'No data found.').classes('text-grey-500 font-semibold ml-1')
                                ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                        except Exception as e:
                            ui.label(f'Could not load details for selected attribute {word}.').classes('text-red-500 font-semibold mt-4')
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')
                            print(e)
            
            def find_persons(attr_type: str, attr_value: str):
                """Find and display a person with specificed attribute type and value."""
                
                search_column.visible = False
                details_column.clear()
                details_column.visible = True
                ui.run_javascript("window.scrollTo(0,0);")

                with details_column:           
                    try:
                        persons = database.get_table("persons")
                        attributes = database.get_table("attributes")

                        stmt = (
                            select(persons.c.id, persons.c.name, attributes.c.the_date)
                            .where(
                                and_(
                                    attributes.c.the_type.like(attr_type),
                                    attributes.c.the_value.like(attr_value),
                                    attributes.c.entity == persons.c.id,
                                )
                            ).order_by(persons.c.name, attributes.c.the_date))

                        with database.session() as session:
                                found_table = session.execute(stmt)
                                table_pd = pd.DataFrame(found_table)
        
                        if table_pd is not None and not table_pd.empty:
                            ui.label(f'List of persons with {attr_type} = {attr_value}').classes('mb-4 text-lg font-bold text-orange-500')

                            ui.add_body_html('''
                                    <style>
                                    .highlight-cell { text-decoration: underline; }
                                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                                    </style>
                                    ''')

                            ui.aggrid({
                                'columnDefs': [
                                    {'headerName': 'ID', 'field': 'id', 'cellClass': 'highlight-cell'},
                                    {'headerName': 'Name', 'field': 'name'},
                                    {'headerName': 'Date', 'field': 'the_date'},
                                ],
                                "pagination": True,
                                "paginationPageSize": 10,
                                "paginationPageSizeSelector": [10, 30, 50, 100],
                                'rowData': table_pd.to_dict("records"),
                            }).classes('h-[70vh]').on('cellClicked', lambda e: load_entity_details(e.args["data"]["id"]) if e.args["colId"] == "id" else None)
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                        else:
                            ui.label(f'No persons with attribute type \"{attr_type}\" and value \"{attr_value}\" combination found.').classes('text-grey-500 font-semibold ml-1')
                            ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')

                    except Exception as e:
                        ui.label(f'Could not load details for selected attribute type/value combination.').classes('text-red-500 font-semibold mt-4')
                        print(e)
                        ui.button('Back to Explore Page', on_click=back_to_explore_cleanup).classes('mt-2')
                    
            
            def load_entity_details(item_id: str):
                "Page to load details on a specific entity."
                
                search_column.visible = False
                details_column.clear()
                details_column.visible = True

                with details_column:
                    ui.markdown('##### **Entity Details**').classes('mb-4 text-orange-500')
                    try:
                        with database.session() as session:
                            entity = database.get_entity(item_id, session=session)
                            entity_kleio = entity.to_kleio()
                        ui.label(f'Displaying details for: {item_id}').classes('text-lg font-semibold')
                        ui.label(entity_kleio)

                    except Exception as e:
                        ui.label(f'Could not load details for selected id {item_id}').classes('text-red-500 font-semibold')
                        print(e)

                    ui.button('Back to Explore Page', on_click=back_to_explore_cleanup)

            
            # "Landing" page for Database Exploration.
            with search_column:
 
                # Search by ID
                ui.label('Search by ID').classes('text-orange-500 text-xl font-bold')
                
                with ui.row():
                    text_input = ui.input(label='Explore Database', placeholder='ID of something (person, source, act, etc..)').classes('w-80 items-center mb-4')
                    search_button = ui.button('Search').classes("items-center mt-4 ml-3 mb-4")
                
                
                # Search by Name
                ui.label('Names').classes('mb-4 text-orange-500 text-xl font-bold')

                with ui.row():
                    for letter in string.ascii_uppercase + '?':
                        ui.label(letter)\
                            .on('click', lambda _, l=letter: display_info(l, "letter"))\
                                .tooltip(f"Show all names started with {letter}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')


                # Search by Attributes
                ui.label('Attributes').classes('mb-4 text-orange-500 text-xl font-bold')
                with ui.row():
                    attr_df = timelink_web_utils.load_data("attributes", database)
                    if attr_df is not None and not attr_df.empty:
                        grouped = attr_df.groupby("the_type")["count"].sum().to_dict()
                        for result in attr_df["the_type"].unique():
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                ui.label(result).on('click', lambda _, l=result: display_info(l, "statistics", "attributes")
                                                    ).tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                                ui.label(str(grouped.get(result, 0))).on('click', lambda _, l=result: display_info(l, "statistics", "attributes")
                                                    ).tooltip(f"Show all results with {result}").classes('-mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                    else:
                        ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

                # Search by Functions
                ui.label('Functions').classes('mb-4 text-orange-500 text-xl font-bold')
                with ui.row():
                    func_df = timelink_web_utils.load_data("functions", database)
                    if func_df is not None and not func_df.empty:
                        grouped = func_df.groupby("the_value")["count"].sum().to_dict()
                        for result in func_df["the_value"].tolist():
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                ui.label(result).on('click', lambda _, l=result: display_info(l, "statistics", "attributes")
                                                    ).tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                                ui.label(str(grouped.get(result, 0))).on('click', lambda _, l=result: display_info(l, "statistics", "attributes")
                                                    ).tooltip(f"Show all results with {result}").classes('-mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                    else:
                        ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

                # Search by Relations
                ui.label('Relations').classes('mb-4 text-orange-500 text-xl font-bold')

                with ui.row():
                    rel_df = timelink_web_utils.load_data("relations", database)
                    if rel_df is not None and not rel_df.empty:
                        grouped = rel_df.groupby("the_type")["count"].sum().to_dict()
                        for result in rel_df["the_type"].tolist():
                            with ui.row().classes("items-center gap-2 no-wrap"):
                                ui.label(result).on('click', lambda _, l=result: display_info(l, "statistics", "relations")
                                                    ).tooltip(f"Show all the values with {result}").classes('mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')
                                ui.label(str(grouped.get(result, 0))).on('click', lambda _, l=result: display_info(l, "statistics", "relations")
                                                    ).tooltip(f"Show all results with {result}").classes('-mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                    else:
                        ui.label("No data found.").classes('mb-4 italic underline text-gray-500')


                # Advanced Search by attribute type and value.
                ui.label('Advanced Options').classes('text-orange-500 text-xl font-bold')
                
                with ui.row():
                    attribute_type_search = ui.input(label='Choose Attribute Type', placeholder='Write an attribute type here...').classes('w-80 items-center mb-4 mr-3')
                    attribute_value_search = ui.input(label='Choose Attribute Value', placeholder='Write an attribute value here...').classes('w-80 items-center mb-4 mr-3')
                    advanced_options_button = ui.button('Show Persons').classes("items-center mt-4 ml-3 mb-4")

                # Show database sources.
                ui.label("Show Sources").on('click', lambda x: display_info(x, "sources", "sources")).classes('mb-4 cursor-pointer text-orange-500 text-xl underline') 


            # Update functionality of text searches.
            search_button.on('click', lambda: load_entity_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))
            text_input.on('keydown.enter', lambda: load_entity_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))

            attribute_type_search.on('keydown.enter', lambda: find_persons(attribute_type_search.value, attribute_value_search.value) if attribute_type_search.value and attribute_value_search.value else ui.notify("You need both attribute type and value to search!"))
            attribute_value_search.on('keydown.enter', lambda: find_persons(attribute_type_search.value, attribute_value_search.value) if attribute_type_search.value and attribute_value_search.value else ui.notify("You need both attribute type and value to search!"))
            advanced_options_button.on('click', lambda: find_persons(attribute_type_search.value, attribute_value_search.value) if attribute_type_search.value and attribute_value_search.value else ui.notify("You need both attribute type and value to search!"))

        
        with ui.tab_panel('faq'):
            """Currently used as a debug page to check for additional information."""
            with ui.row():
                ui.button("Timelink Server Status", on_click=lambda: timelink_web_utils.show_kleio_info(kserver))
                ui.button("Database Status", on_click=lambda: timelink_web_utils.show_table(database))
                ui.button("Update Database from Sources", on_click=lambda this_button: update_from_sources(this_button.sender))


if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])


app.on_startup(initial_setup)
ui.run(title='Timelink Web Interface', port=int(port))