from timelink.web.pages import navbar
from timelink.pandas.entities_with_attribute import entities_with_attribute
from nicegui import ui, run
from sqlalchemy import select, and_
import pandas as pd


class PeopleGroupsNetworks:

    """Page for People, Groups and Networks"""
    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver
        self.current_value = "Attributes"

        @ui.page('/people')
        async def register():
            await self.people_page()

    async def people_page(self):
        with navbar.header():
            ui.page_title("People, Groups and Networks")

            self.rel_options, self.attr_options = await self.build_attr_rel_pair_list()

            with ui.card().tight().classes("w-full border-0 border-gray-300 rounded-none shadow-none"):
                with ui.tabs() as self.tabs:
                    self.people_tab = ui.tab('people', label='People').classes("w-full text-orange-500 font-bold")
                    self.groups_tab = ui.tab('groups', label='Groups').classes("w-full text-orange-500 font-bold")
                    self.network_tab = ui.tab('networks', label='Network').classes("w-full text-orange-500 font-bold")

                with ui.tab_panels(self.tabs, value=self.people_tab).classes('w-full'):
                    with ui.tab_panel(self.people_tab):
                        with ui.row().classes("w-full bg-blue-100 text-lg rounded text-orange-500 font-bold flex justify-center items-center p-4"):
                            ui.label("Search people by")
                            option_select = ui.select(
                                ["Attributes", "Relations"],
                                value=self.current_value,
                                label="Atribute/Relation",
                                on_change=lambda e: self.set_type_options(search_type, e.value)
                            ).classes('w-40')
                            ui.label("with type ")
                            search_type = ui.select(
                                list(self.attr_options.keys()),
                                with_input=True,
                                label="Search for types...",
                                on_change=lambda e: self.set_val_options(search_val, e.value)
                            ).classes('w-50 ml-3')
                            ui.label("and value ")
                            search_val = ui.select([], with_input=True, label="Search for values...").classes('w-70 ml-3')
                            ui.button("Go!").on('click', lambda: self._find_people_with_attributes(option_select.value, search_type.value, search_val.value))

                        with ui.card().tight().classes("w-full bg-gray-50"):
                            self.people_table_display(pd.DataFrame(), "")

                    with ui.tab_panel(self.groups_tab):
                        ui.label("Groups!")
                    with ui.tab_panel(self.network_tab):
                        ui.label("Networks!")

    @ui.refreshable
    def people_table_display(self, pd_results: pd.DataFrame, option: str) -> None:
        """Table to dynamically display results in, depending on selected options."""

        ui.add_body_html('''<style>
                .highlight-cell { text-decoration: underline dotted; }
                .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                </style>''')


        if pd_results is None or pd_results.empty:
            return
        
        if option == "Attributes":

            cols = [
                    {'headerName': 'ID', 'field': 'id', 'checkboxSelection': True, 'cellClass' : 'highlight-cell'},
                    {'headerName': 'Name', 'field': 'name'},
                    {'headerName': 'Type', 'field': 'the_type'},
                    {'headerName': 'Value', 'field': 'the_value'},
                    {'headerName': 'Date', 'field': 'the_date'},
                ]

        else:
            
            cols = [
                    {'headerName': 'ID', 'field': 'id', 'checkboxSelection': True, 'cellClass' : 'highlight-cell'},
                    {'headerName': 'Name', 'field': 'name'},
                    {'headerName': 'Relation Type', 'field': 'relation_type'},
                    {'headerName': 'Relation Value', 'field': 'relation_value'},
                    {'headerName': 'Destination ID', 'field': 'destination_id', 'cellClass' : 'highlight-cell'},
                    {'headerName': 'Destination Name', 'field': 'destination_name'},
                    {'headerName': 'Relation ID', 'field': 'relation_id'},
                    {'headerName': 'Relation Date', 'field': 'relation_date'}
                ]

        display_grid = ui.aggrid({
                    'columnDefs': cols,
                    "pagination": True,
                    "paginationPageSize": 14,
                    'rowData': pd_results.to_dict("records"),
                    'rowSelection': 'multiple',
                }).classes('h-[50vh]')

        display_grid.on(
                    'cellClicked',
                    lambda e: ui.navigate.to(f"/id/{e.args["data"]["id"]}") if e.args["colId"] == "id" or e.args["colId"] == "destination_id" else None
                )

        async def sort_smart_groups():
            rows = await display_grid.get_selected_rows()
            ui.notify("People to be sorted into smart groups:")
            if rows:
                if option == "Attributes":
                    for row in rows:
                        ui.notify(f"{row['name']}, {row['the_type']}, {row['the_value']}")
                else:
                    for row in rows:
                        ui.notify(f"{row['name']}, {row['relation_type']}, {row['relation_value']}")
            else:
                ui.notify('No rows selected.')

        ui.button("Save Smart Group", on_click=sort_smart_groups).classes("mt-4 ml-4 mb-4")

    def set_type_options(self, type_search, value):
        """Set the correct options to be displayed after choosing attributes/relations."""

        if value == "Attributes":
            self.current_value = "Attributes"
            type_search.set_options(list(self.attr_options.keys()))

        else:
            self.current_value = "Relations"
            type_search.set_options(list(self.rel_options.keys()))


    def set_val_options(self, val_search, value):
        """Set the correct options to be displayed after choosing specific attribute/relation type"""
        
        if value:
            if self.current_value == "Attributes":
                val_search.set_options(self.attr_options[value])

            else:
                val_search.set_options(self.rel_options[value])


    async def build_attr_rel_pair_list(self):
        
        attr_table = self.database.get_table("attributes")
        rels_table = self.database.views["nrelations"]
        persons_table = self.database.get_table("persons")

        with self.database.session() as session:

            person_ids = session.execute(select(persons_table.c.id)).scalars().all()

            attr_pairs = session.execute(
                select(
                    attr_table.c.the_type, attr_table.c.the_value
                ).where(
                    attr_table.c.entity.in_(person_ids)
                ).distinct()).all()
            
            rels_pairs = session.execute(
                select(
                    rels_table.c.relation_type, rels_table.c.relation_value
                ).where(
                    rels_table.c.origin_id.in_(person_ids)
                ).distinct()).all()

        rels_options = {}
        for t, v in rels_pairs:
            rels_options.setdefault(t, []).append(v)
        
        attr_options = {}
        for t, v in attr_pairs:
            attr_options.setdefault(t, []).append(v)

        return rels_options, attr_options
    

    async def _find_people_with_attributes(self, option, type, value):
        """Search for people with defined attribute and build table displaying them."""

        if option == None or type == None or value == None:
            ui.notify("You must fill all the fields before querying.", type="warning")
            return

        spin = ui.spinner()
        entity_pd = await run.io_bound(self.load_from_database, self.database, option, type, value)
        spin.set_visibility(False)

        self.people_table_display.refresh(entity_pd, option)


    def load_from_database(self, database, option, type, value):

        persons = database.get_table("persons")
        attributes = database.get_table("attributes")
        relations = self.database.views["nrelations"]

        if option == "Attributes":
            stmt = (
                select(
                    persons.c.id,
                    persons.c.name,
                    attributes.c.the_type,
                    attributes.c.the_value,
                    attributes.c.the_date)
                .where(
                    and_(
                        attributes.c.the_type.like(type),
                        attributes.c.the_value.like(value),
                        attributes.c.entity == persons.c.id,
                    )
                ).order_by(persons.c.name, attributes.c.the_date))
        else:
            stmt = (
                select(
                    persons.c.id,
                    persons.c.name,
                    relations.c.relation_type,
                    relations.c.relation_value,
                    relations.c.destination_id,
                    relations.c.destination_name,
                    relations.c.relation_id,
                    relations.c.relation_date)
                .where(
                    and_(
                        relations.c.relation_type.like(type),
                        relations.c.relation_value.like(value),
                        relations.c.origin_id == persons.c.id,
                    )
                ).order_by(persons.c.name))
            
        with self.database.session() as session:
            found_table = session.execute(stmt)
            table_pd = pd.DataFrame(found_table)

        return table_pd