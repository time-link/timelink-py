from pages import navbar
import timelink_web_utils
import pandas as pd
from datetime import datetime

from nicegui import ui


class Overview:
    
    """Page for an overview of the database and recent activity."""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        @ui.page('/overview')
        async def register():
            await self.overview_page()


    async def overview_page(self):
        with navbar.header():
            ui.page_title("Database Overview")
            ui.markdown(f'#### **Database Overview**').classes('ml-2 mb-4 text-orange-500')

            with ui.card().tight().classes("w-full bg-gray-50"):
                with ui.tabs() as tabs:
                    entity_count_tab = ui.tab('entity_count', label='Entity Count').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    sources_count_tab = ui.tab('source_count', label='Latest Source Status').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    recent_tab = ui.tab('recent_views', label='Recently Viewed').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    important_tab = ui.tab('important_entities', label='Important Entities').classes("w-full bg-gray-70 text-orange-500 font-bold")
                    recent_searches_tab = ui.tab('recent_search', label='Recent Searches').classes("w-full bg-gray-70 text-orange-500 font-bold")
                with ui.tab_panels(tabs, value=entity_count_tab).classes('w-full bg-gray-50'):
                    with ui.tab_panel(entity_count_tab).classes("items-center"):
                        self._display_entity_count()
                    with ui.tab_panel(sources_count_tab).classes("items-center"):
                        self._display_sources_count()
                    with ui.tab_panel(recent_tab).classes("items-center"):
                        self._display_recent_views()
                    with ui.tab_panel(important_tab).classes("items-center"):
                        self._display_important_entities()
                    with ui.tab_panel(recent_searches_tab).classes("items-center"):
                        self._display_recent_searches()
                        


    def _display_entity_count(self):
        """Display count of entities found on the database."""
     
        try:
            entity_pd = timelink_web_utils.get_entity_count_table(self.database)

            expected_cols = [
                    {'headerName': 'Entity Class', 'field': 'pom_class'},
                    {'headerName': 'Count', 'field': 'count'},
                    ]

            ui.aggrid({
                'columnDefs': expected_cols,
                'rowData': entity_pd.to_dict("records")}
            )
            
            with ui.row().classes("w-full"):
                ui.label(f"Total number of entities: ")
                ui.label(entity_pd.loc[entity_pd['pom_class'].isin(['geoentity', 'class', 'source', 'person', 'act']), 'count'].sum()).classes("font-bold")
        
        
        except Exception as e:
            ui.label(f'Could not load entity count - something went wrong: ({e})').classes('text-red-500 font-semibold ml-1')
            print(e)


    def _display_sources_count(self):
        """Display imported sources by date as well as their number of errors / warnings and their respective descriptions"""

        try:
            sources_df = timelink_web_utils.get_recent_sources(self.database)
            expected_cols = [
                    {'headerName': 'Name', 'field': 'name'},
                    {'headerName': 'Path', 'field': 'path'},
                    {'headerName': 'Errors', 'field': 'nerrors'},
                    {'headerName': 'Error Report', 'field': 'error_rpt', 'wrapText': True, 'autoHeight': True},
                    {'headerName': 'Warnings', 'field': 'nwarnings'},
                    {'headerName': 'Warning Report', 'field': 'warning_rpt', 'wrapText': True, 'autoHeight': True},
                    {'headerName': 'Import Date', 'field': 'imported', 'sort': 'desc'},
                    {'headerName': 'Structure', 'field': 'structure'},
                    {'headerName': 'Translator', 'field': 'translator'},
                    {'headerName': 'Translation Date', 'field': 'translation_date'}
                    ]

            grid = ui.aggrid({
                'columnDefs': expected_cols,
                'rowData': sources_df.to_dict("records")
            }).classes('h-[75vh]')

            grid.on('firstDataRendered', lambda: grid.run_grid_method('sizeColumnsToFit'))


        except Exception as e:
            ui.label(f'Could not load recent sources - something went wrong: ({e})').classes('text-red-500 font-semibold ml-1')
            print(e)

    def _display_recent_views(self):
        """Display recently viewed entity history."""

        ui.add_body_html('''<style>
                    .highlight-cell { text-decoration: underline dotted; }
                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                    </style>
                ''')

        try:
            history_df = timelink_web_utils.get_recent_history(self.database)

            expected_cols = [
                    {'headerName': 'Entity ID', 'field': 'entity_id', 'cellClass': 'highlight-cell'},
                    {'headerName': 'Entity Type', 'field': 'entity_type'},
                    {'headerName': 'Event Type', 'field': 'activity_type'},
                    {'headerName': 'Event Description', 'field': 'desc'},
                    {'headerName': 'Time', 'field': 'when', 'sort': 'desc'}
                    ]

            history_grid = ui.aggrid({
                'columnDefs': expected_cols,
                'rowData': history_df.to_dict("records")}
            ).classes('h-[75vh]')

            history_grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["entity_id"]}") if e.args["colId"] == "entity_id" else None)


        except Exception as e:
            ui.label(f'Could not load recently viewed entities - something went wrong: ({e})').classes('text-red-500 font-semibold ml-1')
            print(e)


    def _display_important_entities(self):
        """Display entities that were acessed a lot in an adjustable timeframe."""

        def update_grid(value):
            min_ts, max_ts = value['min'], value['max']
            filtered_history_df = history_df[
                (history_df['when'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").timestamp()) >= min_ts) &
                (history_df['when'].apply(lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S.%f").timestamp()) <= max_ts + 60)
            ]
            new_imp_ent_df = filtered_history_df.groupby(['entity_id', 'entity_type']).size().reset_index(name='number_of_accesses')
            imp_ent_grid.options = {
                'columnDefs': expected_cols,
                'rowData': new_imp_ent_df.to_dict('records')
            }
            imp_ent_grid.update()


        ui.add_body_html('''<style>
                    .highlight-cell { text-decoration: underline dotted; }
                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                    </style>
                ''')

        try:
            history_df = timelink_web_utils.get_recent_history(self.database)

            important_ent_df = history_df.groupby(["entity_id", "entity_type"]).size().reset_index(name="number_of_accesses")

            expected_cols = [
                    {'headerName': 'Entity ID', 'field': 'entity_id', 'cellClass': 'highlight-cell'},
                    {'headerName': 'Entity Type', 'field': 'entity_type'},
                    {'headerName': 'Number of Events', 'field': 'number_of_accesses', 'sort': 'desc'}
                    ]

            imp_ent_grid = ui.aggrid({
                'columnDefs': expected_cols,
                'rowData': important_ent_df.to_dict("records")}
            ).classes('h-[40vh]')

            imp_ent_grid.on('cellClicked', lambda e: ui.navigate.to(f"/id/{e.args["data"]["entity_id"]}") if e.args["colId"] == "entity_id" else None)

            # Date range slider
            min_date = datetime.strptime(history_df["when"].min(), "%Y-%m-%d %H:%M:%S.%f").timestamp()
            max_date = datetime.strptime(history_df["when"].max(), "%Y-%m-%d %H:%M:%S.%f").timestamp()
            slider = ui.range(min=min_date, max=max_date, value={'min': min_date, 'max' : max_date})
            
            with ui.row().classes("w-full justify-between"):
                ui.label().bind_text_from(slider, 'value',
                          backward=lambda v: f'Min Search Date: {datetime.fromtimestamp(v["min"]).strftime("%Y-%m-%d %H:%M")}')
                ui.label().bind_text_from(slider, 'value',
                          backward=lambda v: f'Max Search Date: {datetime.fromtimestamp(v["max"]).strftime("%Y-%m-%d %H:%M")}')

            slider.on('change', lambda e: update_grid(e.args))


        except Exception as e:
            ui.label(f'Could not load important entities - something went wrong: ({e})').classes('text-red-500 font-semibold ml-1')
            print(e)

    def _display_recent_searches(self):
        """Display table with recent searches."""

        try:
            history_df = timelink_web_utils.get_recent_history(self.database, searched_only= True)

            expected_cols = [
                    {'headerName': 'Search Terms', 'field': 'entity_id'},
                    {'headerName': 'Event Type', 'field': 'activity_type'},
                    {'headerName': 'Event Description', 'field': 'desc'},
                    {'headerName': 'Time', 'field': 'when', 'sort': 'desc'}
                    ]

            ui.aggrid({
                'columnDefs': expected_cols,
                'rowData': history_df.to_dict("records")}
            )

        except Exception as e:
            ui.label(f'Could not load recently viewed entities - something went wrong: ({e})').classes('text-red-500 font-semibold ml-1')
            print(e)