from nicegui import ui, app
from timelink_web_utils import run_setup, run_imports_sync
from sqlalchemy import select, func
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
    kserver, database = await run_setup()


def show_kleio_info():
    """Helper function to display Kleio Server Path and other variables."""
    dialog = ui.dialog()
    with dialog, ui.card() as card:

        ui.label('Kleio Server Overview')
        ui.markdown(f"""
        - **Kleio URL:** {kserver.url}  
        - **Kleio Home:** {kserver.kleio_home}
        """)
        ui.button('Close', on_click=dialog.close)

    dialog.open()


def show_table():
    """Helper function to display database."""
    dialog = ui.dialog()
    with dialog, ui.card() as card:
        ui.label('Database Table Overview')

        table_placeholder = ui.column()

        def refresh():
            tables = database.table_row_count()
            df = pd.DataFrame(tables, columns=["Table", "Row Count"])
            table_placeholder.clear()
            with table_placeholder:
                ui.table(
                    columns=[{'name': col, 'label': col, 'field': col} for col in df.columns],
                    rows=df.to_dict(orient='records'),
                    row_key='Table',
                )

        refresh()
        ui.button('Close', on_click=dialog.close)

    dialog.open()


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
            await asyncio.to_thread(run_imports_sync, database)
            ui.notify("Done updating the database!", type="positive")
        except Exception as e:
            ui.notify(f"ERROR: Database import failed: {e}", type="negative")


@ui.page('/')
def index():

    # Helper functions
    def back_to_explore_cleanup():
        """Handle returning from the details of a person."""
        details_column.visible = False
        names_column.visible = False
        search_column.visible = True
        
        if text_input:
            text_input.value = ''

    with ui.header().classes(replace='row items-center') as header:
        with ui.tabs()as tabs:
            ui.tab('explore', label="Explore")
            ui.tab('faq', label="Status Check")

    with ui.footer(value=False) as footer:
        ui.label('Footer')

    with ui.tab_panels(tabs).classes('w-full') as timelink_panels:
        with ui.tab_panel('explore'):
            """Explore Page - search_column will be used for an overview of the available data. details_column will be used for information on specific queries."""
            search_column = ui.column().classes('w-full')
            details_column = ui.column().classes('w-full')
            names_column = ui.column().classes('w-full')
            details_column.visible = False
            names_column.visible = False


            with search_column:
                ui.markdown('#### **Explore Database**').classes('mb-4 text-orange-500')
                ui.markdown('##### **Search by ID**').classes('mb-4 text-orange-500')
                
                with ui.row():
                    text_input = ui.input(label='Explore Database', placeholder='ID of something (person, source, act, etc..)').classes('w-80 items-center')
                    search_button = ui.button('Search').classes("items-center mt-4 ml-3")
                ui.markdown('##### **Names**').classes('mb-4 text-orange-500')

                with ui.row():
                    for letter in string.ascii_uppercase + '?':
                        ui.button(letter, on_click=lambda _, l=letter: load_names(l))
                

            def load_details(item_id: str):
                
                search_column.visible = False
                details_column.clear()
                details_column.visible = True

                with details_column:
                    ui.markdown('##### **Entity Details**').classes('mb-4 text-orange-500')
                    try:
                        with database.session() as session:
                            entity = database.get_entity(item_id, session=session)
                            entity_kleio = entity.to_kleio()
                        ui.label(f'Displaying details for: {item_id}').classes('text-lg font-semibold mt-4')
                        ui.label(entity_kleio)

                    except Exception as e:
                        ui.label(f'Could not load details for selected id {item_id}').classes('text-red-500 font-semibold mt-4')

                    ui.button('Back to Explore Page', on_click=back_to_explore_cleanup)

            
            def load_names(letter: str):
                search_column.visible = False
                names_column.clear()
                names_column.visible = True

                with names_column:
                    ui.markdown(f'#### **All names started with {letter}**').classes('mb-4 text-orange-500')

                    try:
                        person_table = database.get_table('persons')

                        stmt = (
                            select(person_table.c.name, func.count().label("name_count"))
                            .where(person_table.c.name.like(f"{letter}%"))
                            .group_by(person_table.c.name)
                            .order_by(func.count().desc())
                        )

                        with database.session() as session:
                            names_results = session.execute(stmt)
                            names_df = pd.DataFrame(names_results)

                        ui.table.from_pandas(names_df, column_defaults={"sortable": True}).classes("max-h-50")

                    except Exception as e:
                        ui.label(f'Could not load details for selected letter {letter}.').classes('text-red-500 font-semibold mt-4')
                        print(e)

                    ui.button('Back to Explore Page', on_click=back_to_explore_cleanup)

            search_button.on('click', lambda: load_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))
            text_input.on('keydown.enter', lambda: load_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))

        
        with ui.tab_panel('faq'):
            """Currently used as a debug page to check for additional information."""
            with ui.row():
                ui.button("Timelink Server Status", on_click=show_kleio_info)
                ui.button("Database Status", on_click=show_table)
                ui.button("Update Database from Sources", on_click=lambda this_button: update_from_sources(this_button.sender))

if "--port" in sys.argv:
    idx = sys.argv.index("--port") + 1
    if idx < len(sys.argv):
        port = int(sys.argv[idx])


app.on_startup(initial_setup)
ui.run(title='Timelink Web Interface', port=int(port))