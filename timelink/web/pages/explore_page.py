from timelink.web.pages import navbar
from nicegui import ui
import string
from timelink.web import timelink_web_utils


class ExplorePage:

    """Page for database exploration."""
    def __init__(self, timelink_app) -> None:
        self.database = timelink_app.database
        self.kserver = timelink_app.kleio_server

        @ui.page('/explore')
        def register():
            self.explore_page()

    def explore_page(self):
        with navbar.header():

            ui.page_title("Explore Page")

            # Search by ID
            ui.label('Search by ID').classes('text-orange-500 text-xl font-bold')

            with ui.row():
                self.text_input = ui.input(
                    label='Explore Database',
                    placeholder='ID of something (person, source, act, etc..)'
                ).on('keydown.enter', self._handle_id_search).classes('w-80 items-center mb-4')

                ui.button('Search').on('click', self._handle_id_search).classes("items-center mt-4 ml-3 mb-4")

            # Search by Name
            ui.label('Names').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                for letter in string.ascii_uppercase + '?':
                    ui.label(
                        letter
                    ).on(
                        'click',
                        lambda _, clicked_letter=letter:
                        ui.navigate.to(f'/all_tables/persons?display_type=names&value={clicked_letter}')
                    ).tooltip(
                        f"Show all names started with {letter}"
                    ).classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

            # Search by Attributes
            ui.label('Attributes').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                attr_df = timelink_web_utils.load_data("attributes", self.database)
                if attr_df is not None and not attr_df.empty:
                    grouped = attr_df.groupby("the_type")["count"].sum().to_dict()
                    for result in attr_df["the_type"].unique():
                        with ui.row().classes("items-center gap-2 no-wrap"):

                            ui.label(
                                result
                            ).on(
                                'click',
                                lambda _,
                                clicked_attr=result:
                                ui.navigate.to(f'/all_tables/attributes?display_type=statistics&value={clicked_attr}')
                            ).tooltip(
                                f"Show all the values with {result}"
                            ).classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

                            ui.label(
                                str(grouped.get(result, 0))
                            ).on(
                                'click',
                                lambda _,
                                clicked_attr_count=result:
                                ui.navigate.to(f'/tables/attributes?attr_type={clicked_attr_count}')
                            ).tooltip(
                                f"Show all results with {result}"
                            ).classes('highlight-cell -mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Search by Functions
            ui.label('Functions').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                func_df = timelink_web_utils.load_data("functions", self.database)
                if func_df is not None and not func_df.empty:
                    grouped = func_df.groupby("the_value")["count"].sum().to_dict()
                    for result in func_df["the_value"].tolist():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(
                                result
                            ).on(
                                'click',
                                lambda _,
                                clicked_func=result:
                                ui.navigate.to(f'/tables/functions?type={clicked_func}')
                            ).tooltip(
                                f"Show all the values with {result}"
                            ).classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

                            ui.label(
                                str(grouped.get(result, 0))
                            ).classes('-mt-10 text-xs text-blue-500 font-semibold')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Search by Relations
            ui.label('Relations').classes('mb-4 text-orange-500 text-xl font-bold')
            with ui.row():
                rel_df = timelink_web_utils.load_data("relations", self.database)
                if rel_df is not None and not rel_df.empty:
                    grouped = rel_df.groupby("the_type")["count"].sum().to_dict()
                    for result in rel_df["the_type"].tolist():
                        with ui.row().classes("items-center gap-2 no-wrap"):
                            ui.label(result).on(
                                'click',
                                lambda _,
                                clicked_rel=result:
                                ui.navigate.to(f'/all_tables/relations?display_type=statistics&value={clicked_rel}')
                            ).tooltip(
                                f"Show all the values with {result}"
                            ).classes('highlight-cell mb-4 cursor-pointer text-lg text-blue-500 font-semibold underline')

                            ui.label(str(grouped.get(result, 0))).on(
                                'click',
                                lambda _, clicked_rel_count=result: ui.navigate.to(f'/tables/relations?type={clicked_rel_count}')
                            ).tooltip(
                                f"Show all results with {result}"
                            ).classes('highlight-cell -mt-10 cursor-pointer text-xs text-blue-500 font-semibold underline')
                else:
                    ui.label("No data found.").classes('mb-4 italic underline text-gray-500')

            # Advanced Search by attribute type and value.
            ui.label('Advanced Options').classes('text-orange-500 text-xl font-bold')
            with ui.row():
                self.attribute_type_search = ui.input(
                    label='Choose Attribute Type',
                    placeholder='Write an attribute type here...'
                ).on('keydown.enter', self._handle_advanced_search).classes('w-80 items-center mb-4 mr-3')

                self.attribute_value_search = ui.input(
                    label='Choose Attribute Value',
                    placeholder='Write an attribute value here...'
                ).on('keydown.enter', self._handle_advanced_search).classes('w-80 items-center mb-4 mr-3')

                ui.button('Show Persons').on('click', self._handle_advanced_search).classes("items-center mt-4 ml-3 mb-4")

            # Show database sources.
            ui.label("Show Sources").on(
                'click',
                lambda sources: ui.navigate.to(f'/all_tables/sources?display_type=sources&value={sources}')
            ).classes('mb-4 cursor-pointer text-orange-500 text-xl underline')

    def _handle_id_search(self):
        """Handles the search by ID function."""
        if self.text_input.value:
            ui.navigate.to(f'/id/{self.text_input.value}')
        else:
            ui.notify("You need a valid input to search the database.")

    def _handle_advanced_search(self):
        """Handles the advanced search by attribute type and value."""
        if self.attribute_type_search.value and self.attribute_value_search.value:
            ui.navigate.to(f'/tables/persons?value={self.attribute_type_search.value}&type={self.attribute_value_search.value}')
        else:
            ui.notify("You need both attribute type and value to search!")
