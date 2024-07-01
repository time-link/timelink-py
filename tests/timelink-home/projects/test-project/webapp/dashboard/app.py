from shiny.express import ui, render, input
from shinywidgets import render_plotly
import plotly.express as px

import timelink
from timelink.pandas import attribute_types

from shared import tlnb, project_home

ui.h1("Timelink dashboard")

with ui.sidebar(bg="#f8f8f8"):
    "SideBar"

timelink_info = tlnb.print_info()

# Get kleio files
kleio_files_df = tlnb.get_import_status()
kleio_files_df.info()

cols = ["name", "status", "import_status", "directory"]
# tlnb.update_from_sources()

database_status = tlnb.table_row_count_df()

with ui.layout_columns():
    with ui.card(bg="light"):
        "Database status"

        @render.data_frame
        def db_status():
            return database_status

    with ui.card(bg="light"):
        "File status"

        translation_status = {
            "*": "All",
            "T": "T-Needs translation",
            "V": "V-Valid translation",
            "E": "E-Translated with errors",
            "W": "W-Translated with warnings",
        }
        import_status = {
            "*": "All",
            "N": "N-Not imported",
            "U": "U-File updated, needs re-import",
            "I": "I-Imported",
            "E": "E-Imported with errors",
            "W": "W-Imported with warnings",
        }
        with ui.layout_columns():
            ui.input_select(
                "tstatus", "Translation status", translation_status, selected="*"
            )
            ui.input_select(
                "istatus", "Import status", import_status, selected="*")

        @render.data_frame
        def file_status():
            if input.tstatus() == "*":
                tfilter = kleio_files_df.status == kleio_files_df.status
            else:
                tfilter = input.tstatus() == kleio_files_df.status

            if input.istatus() == "*":
                ifilter = kleio_files_df.import_status == kleio_files_df.import_status
            else:
                ifilter = input.istatus() == kleio_files_df.import_status

            return kleio_files_df[(tfilter) & (ifilter)][cols]


types_totals = attribute_types(db=tlnb.db).reset_index()
types_totals.info()

with ui.card(bg="light"):
    "Attribute types"

    @render_plotly
    def plot_top_types():
        top_types = types_totals.sort_values("count", ascending=False).head(10)
        return px.bar(top_types, x="type", y="count", title="Top 10 attribute types")

    @render.data_frame
    def totals():
        return types_totals.sort_values("count", ascending=False)


ui.hr()
ui.p(f"Timelink project home: {project_home}")
ui.p(f"Timelink version: {timelink.__version__}")
