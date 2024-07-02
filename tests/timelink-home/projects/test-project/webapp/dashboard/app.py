from shiny import reactive
from shiny.express import ui, render, input
from shinywidgets import render_plotly
import plotly.express as px

import timelink
from timelink.pandas import attribute_types, attribute_values

from shared import tlnb, project_home
from shared import task_queue, task_running, context

ui.h1("Timelink dashboard")

with ui.sidebar(bg="#f8f8f8"):
    "SideBar"

timelink_info = tlnb.print_info()

# Get kleio files status

kleio_files_df = tlnb.get_import_status()
kleio_files_df.info()


@reactive.calc()
@reactive.event(input.refresh_files, ignore_init=False)
def refresh_files():
    print("Files refreshed")
    return tlnb.get_import_status()


@reactive.calc()
def filter_files():

    kleio_files_df = refresh_files()

    if input.tstatus() == "*":
        tfilter = kleio_files_df.status == kleio_files_df.status
    else:
        tfilter = input.tstatus() == kleio_files_df.status

    if input.istatus() == "*":
        ifilter = kleio_files_df.import_status == kleio_files_df.import_status
    else:
        ifilter = input.istatus() == kleio_files_df.import_status
    return kleio_files_df[(tfilter) & (ifilter)]


@reactive.effect()
@reactive.event(input.update_sources)
def update_from_sources():
    task_queue.put((tlnb.update_from_sources, (), {}))


database_status = tlnb.table_row_count_df()


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
        cols = ["name", "status", "import_status", "directory"]
        kleio_files = filter_files()
        return kleio_files[cols]

    ui.input_action_button("refresh_files", "Refresh files")
    if task_running.is_set():
        ui.p("Task running")
    ui.input_action_button("update_sources", "Update from sources")

types_totals = attribute_types(db=tlnb.db)
types_totals.info()
unique_types = types_totals["type"].nunique()

with ui.card(bg="light"):
    "Attribute types"

    ui.input_slider("top_types", "Top types", min=1, max=types_totals.size, step=1, value=10)

    @render_plotly
    def plot_top_types():
        show_only = input.top_types()  # number of top types to show
        top_types = types_totals.sort_values("count", ascending=False).head(show_only)
        return px.bar(top_types, x="type", y="count", title=f"Top {show_only} attribute types")

    @render.data_frame
    def totals():
        return types_totals.sort_values("count", ascending=False)

    ui.input_select("unique_types", "Unique types", sorted(types_totals["type"]), selected=False)

    @render.data_frame
    def values():
        if input.unique_types():
            return attribute_values(db=tlnb.db, attr_type=input.unique_types()).reset_index()
        return None

ui.hr()
ui.p(f"Timelink project home: {project_home}")
ui.p(f"Timelink version: {timelink.__version__}")
