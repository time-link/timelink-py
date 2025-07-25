from pages import navbar
from nicegui import ui
import timelink_web_utils
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

template_dir = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(template_dir))

class DisplayIDPage:
    """Page to display entities with specified ID"""

    def __init__(self, database, kserver) -> None:
        self.database = database
        self.kserver = kserver

        self.accepted_relations = ["eclesiástica", "geografica", "institucional", "parentesco", "profissional", "sociabilidade", "identification"]

    def register(self):
        @ui.page('/id/{item_id}')
        def display_id_page(item_id: str):
            """Display an entity with a specific ID."""
            
            with navbar.header():
                display_func_map = {
                        "person": self._display_person,
                        "geoentity": self._display_geoentity,
                        "act": self._display_act,
                        "source": self._display_act,
                        "relation": self._display_act,
                        "attribute": self._display_act
                    }
                
                ui.add_body_html('''<style>
                    .highlight-cell { text-decoration: underline dotted; }
                    .highlight-cell:hover { color: orange; font-weight: bold; cursor: pointer; }
                    </style>
                ''')
                
                try:
                    with self.database.session() as session:
                        entity = self.database.get_entity(item_id, session=session)
                        if entity:
                            display_func = display_func_map.get(entity.pom_class)
                            if display_func:
                                display_func(entity)
                            else:
                                ui.label(f"No page created for {entity.pom_class} yet.").classes('mb-4 text-lg font-bold text-red-500')
                        else:
                            ui.label(f"No entity with value {item_id} found.").classes('mb-4 text-lg font-bold text-red-500')

                except Exception as e:
                    ui.label(f'Could not load details for selected entity.').classes('text-red-500 font-semibold mt-4')
                    print(e)

                
    def _display_person(self, entity: Entity):
        "Page to load details on an entity of type person."

        ui.page_title(f"Results for {entity.id}")

        first_card_rendered = False

        with ui.row():
            ui.label(entity.name).on('click', lambda: ui.navigate.to(f'/tables/persons?value={entity.name}')).classes('cursor-pointer underline decoration-dotted text-xl font-bold')
            ui.label(f"id: {entity.id}").classes('text-xl font-bold text-orange-500')
        
        with ui.row().classes('items-center gap-1'):
                ui.label('groupname:').classes('text-orange-500')
                ui.label(entity.groupname).classes('mr-3 text-blue-400')
                ui.label('sex:').classes('text-orange-500')
                ui.label(entity.sex).classes('mr-3 text-blue-400')
                ui.label('line:').classes('text-orange-500')
                ui.label(entity.the_line).classes('mr-3 text-blue-400')

        parsed_attributes, parsed_relations_in, parsed_relations_out = timelink_web_utils.parse_entity_details(entity)

        with ui.card().tight().classes("w-full bg-gray-50"):
            with ui.tabs() as tabs:
                person_info_tab = ui.tab('p_info', label='Person Info').classes("w-full bg-blue-100 text-orange-500 font-bold")
            with ui.tab_panels(tabs, value=person_info_tab).classes('w-full bg-gray-50'):
                with ui.tab_panel(person_info_tab).classes("items-center"):
                    with ui.grid(columns=9).classes("w-full bg-blue-100 text-orange-500 font-bold"):
                        ui.label("Name").classes("text-center")
                        ui.label("Function").classes("text-center")
                        ui.label("Date").classes("text-center")
                        ui.label("Attributes").classes("break-all col-span-4 text-center")
                        ui.label("Relations").classes("text-center col-span-2 text-center")
                        
                    for date, pairs in sorted(parsed_attributes.items()):
                        with ui.card().tight().classes("w-full border-0 border-b border-gray-300 rounded-none shadow-none bg-gray-50"):
                            with ui.grid(columns=9).classes("w-full items-start gap-4 text-xs"):
                                
                                # Only display name function and relations once.
                                if not first_card_rendered:
                                    
                                    # ---- Display Name ----
                                    ui.label(entity.name).classes("ml-1 mt-1 mb-1")

                                    # --- Function Column ---
                                    with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                        for function in parsed_relations_out:
                                            if function["the_type"] not in self.accepted_relations:
                                                with ui.row().classes("no-wrap"):
                                                    ui.label(f'{function["dest_name"]} : {function["the_value"]}').on(
                                                        "click", lambda _, id=function["destination"]: ui.navigate.to(f'/id/{id}')
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')

                                else:
                                    ui.space().classes("col-span-2 ml-1 mt-1 mb-1")

                                # --- Show Date ---
                                with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                    ui.label(timelink_web_utils.format_date(date)).classes("text-blue-600 font-bold")


                                # --- Attributes Column ---
                                with ui.column().classes("col-span-4 ml-1 mt-1 mb-1 items-right justify-center"):
                                    with ui.row().classes("items-start mr-1 no-wrap"):
                                        with ui.column():
                                            for i, entry in enumerate(pairs):
                                                with ui.row().classes("no-wrap mb-3"):
                                                    ui.label(entry.the_type).on(
                                                        "click", lambda _, k=entry.the_type: ui.navigate.to(f'/all_tables/attributes?display_type=statistics&value={k}')
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                    ui.label(":")
                                                    ui.label(entry.the_value).on(
                                                        "click", lambda _, k=entry.the_type, v=entry.the_value: ui.navigate.to(f'/tables/persons?value={k}&type={v}')
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                    if entry.obs:
                                                        ui.label(entry.obs)
                                                if i < len(pairs) - 1:
                                                    ui.separator().classes("-mt-2")

                                # --- Relations Column ---
                                if not first_card_rendered:
                                    with ui.column().classes("col-span-2 ml-1 mt-1 mb-1"):
                                        for rel in parsed_relations_in:
                                            with ui.row().classes("no-wrap"):
                                                ui.label("tem como")
                                                ui.label(rel["the_value"]).on(
                                                    "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["org_name"]: ui.navigate.to(f'/tables/relations?type={type}&value={value}&id={id}&is_from=True')
                                                ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                                ui.label(" : ")
                                                ui.label(rel["org_name"]).on(
                                                    "click", lambda _, id=rel["origin"]: ui.navigate.to(f'/id/{id}')
                                                ).classes('highlight-cell cursor-pointer decoration-dotted')


                                        for rel in parsed_relations_out:
                                            if rel["the_type"] in self.accepted_relations:
                                                with ui.row().classes("no-wrap"):
                                                    ui.label(rel["the_value"]).on(
                                                        "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["dest_name"]: ui.navigate.to(f'/tables/relations?type={type}&value={value}&id={id}&is_from=False')
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                    ui.label("de:").classes('-ml-3')
                                                    ui.label(rel["dest_name"]).on(
                                                        "click", lambda _, id=rel["destination"]: ui.navigate.to(f"/id/{id}")
                                                    ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')

                                        ui.space().classes("mb-2")
                                else:
                                    ui.space().classes("col-span-2 ml-1 mt-1 mb-1")
                                
                                first_card_rendered = True


    def _display_geoentity(self, entity: Entity):
        "Page to load details on an entity of type person."


        with ui.row():
            ui.label(entity.name).on('click', lambda: ui.navigate.to(f"/tables/geoentities?name={entity.name}")).classes('cursor-pointer underline decoration-dotted text-xl font-bold')
        
        with ui.row().classes('items-center gap-1'):
                ui.label('id:').classes('text-orange-500')
                ui.label(entity.id).classes('mr-3 text-blue-400')
                ui.label('inside:').classes('text-orange-500')
                ui.label(entity.inside).on('click', lambda: ui.navigate.to(f"/id/{entity.inside}")).classes('mr-3 cursor-pointer underline decoration-dotted')
                ui.label('Full file:').classes('text-orange-500')


        parsed_attributes, parsed_relations_in, parsed_relations_out = timelink_web_utils.parse_entity_details(entity)
        first_card_rendered = False
        
        with ui.card().tight().classes("w-full bg-gray-50"):
            with ui.tabs() as tabs:
                geo_info_tab = ui.tab('p_info', label='Geoentity Details').classes("w-full bg-blue-100 text-orange-500 font-bold")
            with ui.tab_panels(tabs, value=geo_info_tab).classes('w-full'):
                with ui.tab_panel(geo_info_tab).classes("items-center"):
                    with ui.grid(columns=6).classes("w-full bg-blue-100 text-orange-500 font-bold"):
                        ui.label("Name").classes("text-center")
                        ui.label("Functions").classes("text-center")
                        ui.label("Attributes").classes("text-center col-span-2")
                        ui.label("Relations").classes("text-center col-span-2")

                    for _, pairs in sorted(parsed_attributes.items()):
                        with ui.card().tight().classes("w-full border-0 border-b border-gray-300 rounded-none shadow-none bg-gray-50"):
                            with ui.grid(columns=6).classes("w-full items-start gap-4 text-xs"):

                                if not first_card_rendered:
                                
                                    # --- Name Column ---
                                    with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                        ui.label(entity.name).classes("ml-1 mt-1 mb-1")

                                    # --- Functions Column ---
                                    with ui.column().classes("col-span-1 ml-1 mt-1 mb-1"):
                                        for function in parsed_relations_out:
                                            if function["the_type"] not in self.accepted_relations:
                                                with ui.row().classes("no-wrap"):
                                                    ui.label(f'{function["dest_name"]} : {function["the_value"]}').on(
                                                    "click", lambda _, id=function["destination"]: ui.navigate.to(f"/id/{id}")).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                
                                # --- Attributes Column ---
                                with ui.column().classes("col-span-2 ml-1 mt-1 mb-1 items-righ"):
                                    for i, entry in enumerate(pairs):
                                        with ui.row().classes("items-start mr-1 no-wrap mb-3"):
                                                ui.label(entry.the_type).classes('font-bold')
                                                ui.label(":")
                                                ui.label(entry.the_value)
                                                if entry.obs:
                                                    ui.label(entry.obs)
                                        if i < len(pairs) - 1:
                                            ui.separator().classes("-mt-2")                                                              
                                        
                                # --- Relations Column ---
                                if not first_card_rendered:
                                    with ui.column().classes("col-span-2 ml-1 mt-1 mb-1"):
                                            for rel in parsed_relations_in:
                                                with self.database.session() as session:
                                                    original_entity = self.database.get_entity(rel["origin"], session=session)
                                                    with ui.row().classes("no-wrap"):
                                                        ui.label("tem como")
                                                        ui.label(rel["the_value"]).on(
                                                            "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["org_name"]: ui.navigate.to(f'/tables/relations?type={type}&value={value}&id={id}&is_from=True')
                                                            ).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                                        ui.label(" : ")
                                                        ui.label(original_entity.name).on(
                                                            "click", lambda _, id=rel["origin"]: ui.navigate.to(f"/id/{id}")).classes('highlight-cell cursor-pointer decoration-dotted')
                                            
                                            for rel in parsed_relations_out:
                                                if rel["the_type"] in self.accepted_relations:
                                                    with self.database.session() as session:
                                                        original_entity = self.database.get_entity(rel["origin"], session=session)
                                                        with ui.row().classes("no-wrap"):
                                                            ui.label(rel["the_value"]).on(
                                                                "click", lambda _, type=rel["the_type"], value=rel["the_value"], id=rel["dest_name"]: ui.navigate.to(f'/tables/relations?type={type}&value={value}&id={id}&is_from=False')
                                                                ).classes('highlight-cell cursor-pointer decoration-dotted')
                                                            ui.label("de").classes('-ml-3')
                                                            ui.label(original_entity.name).on(
                                                                "click", lambda _, id=rel["origin"]: ui.navigate.to(f"/id/{id}")).classes('highlight-cell cursor-pointer decoration-dotted -ml-3')
                                
                        first_card_rendered == True

    def _display_act(self, entity: Entity):
        "Page to load details on an entity of type act."


        if entity.the_type:
            ui.page_title(f"{entity.the_type.title()} = {entity.id.title()}")
        else:
            ui.page_title(entity.id.title())


        entity_map = {
            "act": f"/tables/acts?name={entity.the_type}",
            "source": f'/all_tables/sources?display_type=sources&value={entity.the_type}',
            "relation": f'/tables/relations?type={entity.the_type}',
            "attribute": f'/tables/attributes?attr_type={entity.the_type}'
        }

        display_page = entity_map.get(entity.pom_class)
        html_page = env.get_template("act.html").render(entity=entity)
        ui.add_body_html(html_page)
         
        #self._render_act_entity(entity, level=0)  #TODO - ASYNC


    def _render_act_entity(self, entity, level=0):
    
        with self.database.session() as session:
            all_ids = self._collect_all_ids(entity, session)

            preloaded = {
                item_id: self.database.get_entity(item_id, session=session)
                for item_id in all_ids
            }

            self._render_act_entity_recursive(entity, level, preloaded)


    def _collect_all_ids(self, entity, session):
        """Query the database for all the required IDs at once.

        Args:
            entity: entity to collect ids from
            session: current database session.
        
        """
        ids = []

        def recurse(ent):
            act_dict = EntityAttrRelSchema.model_validate(ent).model_dump(exclude=['rels_in'])
            for item in act_dict.get("contains", []):
                ids.append(item["id"])
                child = self.database.get_entity(item["id"], session=session)
                recurse(child)

        recurse(entity)
        return ids



    def _render_act_entity_recursive(self, entity, level, preloaded):
        indent = f"ml-{level * 4}"


        """
        with ui.row():
            if not act_dict['groupname'] == "relation":
                ui.label(f"{act_dict['groupname']}$").classes(f"font-bold {indent}")

                if act_dict['groupname'] not in {"n", "pai", "mae", "pad", "mad", "mrmad"}:
                    ui.label(act_dict['id']).classes(f"-ml-3")

                    for extra_info_key, extra_info_value in act_dict["extra_info"].items():
                        if extra_info_key not in {'class'}:
                            value = getattr(entity, extra_info_key)
                            kleio_class = extra_info_value.get('kleio_element_class')
                            if kleio_class == "obs":
                                obs = f"{value}{extra_info_value.get('comment', '')}"
                            else:
                                ui.label(f"/{kleio_class}=").classes(f'-ml-4 text-green-800')
                                if kleio_class in {'inside', 'id'}:
                                    ui.label(value).on(
                                        "click", lambda _, id=value: ui.navigate.to(f"/id/{id}")
                                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-4')
                                else:
                                    ui.label(value).classes(f'-ml-4')

                    ui.label("/inside=").classes(f'-ml-4')
                    ui.label(entity.inside).on(
                        "click", lambda: ui.navigate.to(f"/id/{entity.inside}")
                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-4') if entity.inside else ui.label("root").classes(f"-ml-4")

                else:
                    ui.label(getattr(entity, 'name')).on(
                        lambda _, id=getattr(entity, 'id'): ui.navigate.to(f"/id/{id}")
                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-3')
                    ui.label(f"/sex={getattr(entity, 'sex')}").classes(f"-ml-3 text-green-800")
                    ui.label(f"/id=").classes(f"-ml-3 text-green-800")
                    ui.label(getattr(entity, 'id')).on(
                        "click", lambda _, id=getattr(entity, 'id'): ui.navigate.to(f"/id/{id}")
                    ).classes(f'highlight-cell cursor-pointer decoration-dotted -ml-3')

        if obs:
            ui.label(f"/obs={obs}").classes(f"font-mono italic text-sm")
        
        for contained_element in act_dict.get("contains", []):
            new_entity = preloaded[contained_element['id']]
            self._render_act_entity_recursive(new_entity, level + 1, preloaded)
    """