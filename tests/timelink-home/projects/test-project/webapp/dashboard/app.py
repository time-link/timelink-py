from functools import partial
from shiny import reactive
from shiny.ui import page_navbar
from shiny.express import ui, render, input
from shinywidgets import render_plotly
import plotly.express as px

from timelink.pandas import attribute_types, attribute_values

from shared import tlnb
from shared import task_queue, task_running, context

ui.page_opts(
    title="Timelink",
    page_fn=partial(page_navbar, id="page", position='static-top', bg="blue", inverse=True),
)

# ==============================
# Timelink overview
# ==============================

with ui.nav_panel("Overview"):

    with ui.card(width="80%"):

        with ui.layout_columns(col_widths=[3, 3, 6]):
            ui.input_checkbox("show_token", "Show token", False)
            ui.input_checkbox("show_password", "Show password", False)

            @render.text(inline=True)
            def db_password_warning():
                if context.get("dbtype", "") == "sqlite" and input.show_password():
                    return "No password is shown for SQLite databases"

        @render.data_frame
        def show_timelink_info():
            df = tlnb.get_info(
                show_token=input.show_token(),
                show_password=input.show_password(),
                as_dataframe=True,
            )
            return render.DataGrid(df, width="80%")


# ==============================
# Timelink sources
# ==============================
with ui.nav_panel("Sources"):
    "Sources"
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
    @reactive.event(input.update_sources, ignore_init=False)
    def update_from_sources():
        task_queue.put((tlnb.update_from_sources, (), {}))

    translation_status = {
        "*": "All",
        "T": "T-Needs translation",
        "V": "V-Valid translation",
        "E": "E-Translated with errors",
        "W": "W-Translated with warnings",
        "P": "P-Processing",
        "Q": "Q-Queued",
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
        cols = ["name", "status", "import_status", "directory", "rpt_url"]
        kleio_files = filter_files()
        return render.DataGrid(kleio_files[cols], filters=False, selection_mode="row")

    ui.input_action_button("refresh_files", "Refresh files")
    ui.input_action_button("update_sources", "Update from sources")

    @render.text(inline=True)
    @reactive.event(input.refresh_files, ignore_init=False)
    def is_task_running():
        if task_running.is_set():
            return "Update underway"
        else:
            return "No updates in progress"

    @reactive.calc()
    def show_selected_file():
        selected_file = file_status.cell_selection()
        if selected_file is None:
            return None
        print(selected_file)
        if len(selected_file["rows"]) == 0:
            return None

        row = selected_file["rows"][0]
        print("Row", row)

        df = file_status.data_view()

        rpt = tlnb.get_translation_report(df, row)

        return rpt
    ui.hr()

    @render.code
    def selected_file():
        return show_selected_file()

    ui.hr()
# ==============================
# Timelink database
# ==============================

with ui.nav_panel("Database"):

    database_status = tlnb.table_row_count_df()

    @render.data_frame
    def db_status():
        return database_status

    # Attribute types and values
    types_totals = attribute_types(db=tlnb.db)
    types_totals.info()
    unique_types = types_totals["type"].nunique()

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
