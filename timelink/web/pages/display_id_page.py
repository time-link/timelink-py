from pages import navbar
from nicegui import ui, run, background_tasks
import timelink_web_utils
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import asyncio
import time

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
        async def display_id_page(item_id: str):
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
                                if asyncio.iscoroutinefunction(display_func):
                                    await display_func(entity)
                                else:
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


    async def _display_act(self, entity: Entity):
        "Page to load details on an entity of type act."

        if entity.the_type:
            ui.page_title(f"{entity.the_type.title()} = {entity.id.title()}")
        else:
            ui.page_title(entity.id.title())


        func_dict = {
            "parse_act_header_string": self._parse_act_header_string,
            "parse_act_body_strings": self._parse_act_body_strings
        }


        header_html_template = env.get_template("act_header.html")
        header_html_template.globals.update(func_dict)
        header_html_render = header_html_template.render(entity=entity)


        # Show spinner while loading
        spinner = ui.spinner(size="lg")
        spinner.visible = True
        entity_childs_list = await run.io_bound(self._collect_all_ids, entity=entity)
        spinner.visible = False  # Hide spinner after load


        body_html_template = env.get_template("act_body.html")
        body_html_template.globals.update(func_dict)
        body_html_render = body_html_template.render(entity_childs=entity_childs_list)

        ui.add_body_html(header_html_render)
        ui.add_body_html(body_html_render)
    

    def _collect_all_ids(self, entity):
           
        with self.database.session() as session:
        
            childs_list = []

            def recurse(ent, level):
                act_dict = EntityAttrRelSchema.model_validate(ent).model_dump(exclude=['rels_in'])
                for item in act_dict.get("contains", []):
                    child = self.database.get_entity(item["id"], session=session)
                    child_dict = EntityAttrRelSchema.model_validate(child).model_dump(exclude=['rels_in'])
                    child_dict["extra_attrs"] = {}
                    
                    for attr in child_dict.get("extra_info", {}).keys():
                        if attr != "class":
                            child_dict["extra_attrs"][child_dict["extra_info"][attr]["kleio_element_class"]] = getattr(child, attr, None)
                    
                    child_dict["extra_attrs"]["inside"] = child.inside

                    child_dict["level"] = level
                    childs_list.append(child_dict)
                    recurse(child, level+1)

            recurse(entity, 1)
        

        return childs_list

    def _parse_act_header_string(self, entity):
        """Parse the entity's attributes to render it properly on a Jinja Template
        
        Args:

            entity:         The entity to be parsed.
        
        """

        act_dict = EntityAttrRelSchema.model_validate(entity).model_dump(exclude=['rels_in'])
        
        entity_string = f"<strong>{act_dict['groupname']}</strong>$ {entity.the_type}"

        obs = ""

        for extra_info_key, extra_info_value in act_dict["extra_info"].items():
            if extra_info_key not in {'class'}:
                value = getattr(entity, extra_info_key)
                kleio_class = extra_info_value.get('kleio_element_class')
                if kleio_class == "obs":
                    obs = f"{value}{extra_info_value.get('comment', '')}"
                elif kleio_class == "id":
                    entity_string += f"/{kleio_class}=<span class='highlight-cell' onclick=\"window.location.href='/id/{value}'\">{value}</span> "
                else:
                    entity_string += f'/<span class="title-definition">{kleio_class}=</span>{value} '

        if entity.inside: 
            entity_string += f"/inside=<span class='highlight-cell' onclick=\"window.location.href='/id/{entity.inside}'\">{entity.inside}</span> "
        else:
            entity_string += f"/inside=root"

        if obs:
            entity_string += f'<span class="mono">\n/obs={obs}</span>'
        
        return entity_string
    

    def _parse_act_body_strings(self, ent_dict):
        
        
        if ent_dict["groupname"] == "relation" and ent_dict["extra_attrs"].get("type") == "function-in-act":
            return ""

        level_indent = "\t" * ent_dict["level"]
        entity_string = f"{level_indent}<strong>{ent_dict['groupname']}</strong>$ "

        extra = ent_dict["extra_attrs"]
        eid = ent_dict["id"]

        if ent_dict['groupname'] in {"fonte", "lista", "geodesc", "bap"}:
            entity_string += (
                f"{eid}"
                f'/<span class="title-definition">date</span>={extra["date"]} '
                f'/<span class="title-definition">type</span>={extra["type"]} '
                f"/inside={timelink_web_utils.highlight_link(f'/id/{extra['inside']}', extra['inside'])} "
                f"/id={timelink_web_utils.highlight_link(f'/id/{eid}', extra['id'])} "
            )
        
        elif ent_dict["groupname"] in {"rel", "relation"}:

            entity_string += (
                f" {extra['type']} "
                f"/ {extra['value']} "
                f"/ {timelink_web_utils.highlight_link(f'/id/{extra['destination']}', extra['destination'])} "
                f"/ {timelink_web_utils.format_date(extra['date'])} "
            )


        elif ent_dict["groupname"] in {"ls", "atr"}:
            entity_string += (
                f" {timelink_web_utils.highlight_link(f'/all_tables/attributes?display_type=statistics&value={extra['type']}', extra['type'])} "
                f"/ {timelink_web_utils.highlight_link(f'/tables/persons?value={extra['type']}&type={extra['value']}', extra['value'])} "
                f"/ {timelink_web_utils.format_date(extra['date'])} "
            )
            if "obs" in extra:
                entity_string += timelink_web_utils.format_obs(extra["obs"], ent_dict["level"])

        elif ent_dict["groupname"].startswith("geo"):
            entity_string += (
                f"{timelink_web_utils.highlight_link(f'/id/{eid}', extra['name'])} "
                f'/<span class="title-definition">type</span>={extra["type"]} '
                f"/id={timelink_web_utils.highlight_link(f'/id/{eid}', eid)} "
            )

        else:
            entity_string += (
                f"{timelink_web_utils.highlight_link(f'/id/{eid}', extra['name'])} "
                f'/<span class="title-definition">sex</span>={extra["sex"]} '
                f"/id={timelink_web_utils.highlight_link(f'/id/{eid}', eid)} "
            )


        return entity_string