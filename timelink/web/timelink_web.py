from nicegui import ui
from timelink_web_utils import run_setup
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

kserver = None
database = None
kserver, database = run_setup()

def show_table():
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


@ui.page('/details/{item_id}')
def explore_id_page(item_id: str):
    # Include the header on the details page
    with ui.header().classes(replace='row items-center') as header:
        with ui.tabs() as tabs:
            # You might want to make one of these tabs active or provide a different set of tabs for the details page
            ui.tab('explore', label="Explore")
            ui.tab('faq', label="Status Check")

    ui.label(f'This page will display information on ID: {item_id}')
    # The 'text' variable is not available in this scope, so navigate back to the root
    ui.button('Back to Explore Page', on_click=lambda: ui.navigate.to('/'))


@ui.page('/')
def index():

    # Helper functions
    def back_to_explore():
        """Handle returning from the details of a person."""
        details_column.visible = False
        search_column.visible = True
        
        if text_input:
            text_input.value = ''

    with ui.header().classes(replace='row items-center') as header:
        with ui.tabs(value="home") as tabs:
            ui.tab('home', label="Home")
            ui.tab('explore', label="Explore")
            ui.tab('faq', label="Status Check")

    with ui.footer(value=False) as footer:
        ui.label('Footer')

    with ui.tab_panels(tabs).classes('w-full') as timelink_panels:
        with ui.tab_panel('home'):
            """Timelink Home Panel"""
            ui.markdown("### Welcome to the Timelink Web Interface!")
        with ui.tab_panel('explore'):
            """Explore Page - search_column will be used for an overview of the available data. details_column will be used for information on specific queries."""
            search_column = ui.column().classes('w-full')
            details_column = ui.column().classes('w-full')
            details_column.visible = False

            with search_column:
                ui.markdown('#### **Explore Page**').classes('mb-4')
                text_input = ui.input(label='Explore Database', placeholder='ID of something (person, source, act, etc..').classes('w-80')
                search_button = ui.button('Search')


            def load_details(item_id: str):
                search_column.visible = False
                details_column.clear()
                details_column.visible = True

                with details_column:
                    ui.label(f'Displaying details for: {item_id}').classes('text-lg font-semibold mt-4')
                    ui.label(f'You searched for: {item_id}').classes('text-md mt-2')
                    ui.button('Back to Explore Page', on_click=back_to_explore)

            search_button.on('click', lambda: load_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))
            text_input.on('keydown.enter', lambda: load_details(text_input.value) if text_input.value else ui.notify("You need a valid input to search the database."))
        
        with ui.tab_panel('faq'):
            """Currently used as a debug page to check for additional information."""
            ui.markdown(f"""
            - **Kleio URL:** {kserver.url}  
            - **Kleio Home:** {kserver.kleio_home}
            """)
            ui.button("Display Database Status", on_click=show_table)


ui.run(title='Timelink Web Interface')