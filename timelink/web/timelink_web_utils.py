from nicegui import ui, app
from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from timelink.web.models import Activity
from timelink.web.backend.solr_wrapper import SolrWrapper
from timelink.web.backend.timelink_app_wrapper import TimelinkWebApp
from pathlib import Path
from sqlalchemy import select, func
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from starlette_admin.contrib.sqla import Admin, ModelView
from starlette_admin.views import Link

from timelink.web.pages import (status_page, explore_page,
                                display_id_page, tables_page, overview_page,
                                people_page, families_page, calendar_page,
                                linking_page, sources_page, search_page)
from timelink.web.models.project import Project, ProjectAccess
from timelink.web.models.user import User, UserProperty


def run_imports_sync(db):
    print("Attempting to update database from sources...")
    db.update_from_sources(match_path=True)
    print("Database successfully updated!")


def run_solr_client_setup():
    """ Configure Solr instance based on passed initialization parameters. """

    solr_manager = SolrWrapper(
        solr_container_name="timelink_solr",
        solr_port="8983",
        solr_core_name="timelink_core"
    )

    solr_manager.setup_solr_container()

    solr_manager.init_solr_client()

    return solr_manager


async def run_setup(home_path: Path, job_scheduler: AsyncIOScheduler, database_type: str = "sqlite"):
    """ Load configuration environment variables, connect to kleio server and make the database."""

    solr_manager = run_solr_client_setup()

    timelink_web_app_settings = TimelinkWebApp(
        home_url=home_path,
        db_type=database_type,
        solr_manager=solr_manager,
        job_scheduler=job_scheduler)

    return timelink_web_app_settings


def setup_pages_and_database(timelink_app_settings, project_list, active_project: Project = None):
    """Register all pages on the website after the appropriate database is loaded"""

    timelink_app_settings.load_config_for_project_list(project_list, active_project)

    timelink_app_settings.projects_loaded = True

    explore_page.ExplorePage(timelink_app=timelink_app_settings)

    id_page = display_id_page.DisplayIDPage(timelink_app=timelink_app_settings)
    id_page.register()

    table_page = tables_page.TablesPage(timelink_app=timelink_app_settings)
    table_page.register()

    overview_page.Overview(timelink_app=timelink_app_settings)

    people_page.PeopleGroupsNetworks(timelink_app=timelink_app_settings)

    families_page.Families(timelink_app=timelink_app_settings)

    calendar_page.CalendarPage(timelink_app=timelink_app_settings)

    linking_page.Linking(timelink_app=timelink_app_settings)

    source_page = sources_page.Sources(timelink_app=timelink_app_settings)

    status_page.StatusPage(timelink_app=timelink_app_settings, sources=source_page)

    search_page.Search(timelink_app=timelink_app_settings)

    # Starlette Admin setup
    admin_app = Admin(engine=timelink_app_settings.users_db.engine, title="Timelink Web Admin Panel")
    admin_app.add_view(ModelView(User))
    admin_app.add_view(ModelView(UserProperty, label="User Properties"))
    admin_app.add_view(ModelView(Project))
    admin_app.add_view(ModelView(ProjectAccess, label="Project Access"))
    admin_app.add_view(Link(label="⬅️ Back to the App", url="/"))
    admin_app.mount_to(app)

    ui.navigate.to("/")


def show_table(database: TimelinkDatabase):
    """Helper function to display database."""
    dialog = ui.dialog()
    with dialog, ui.card():
        ui.label('Database Table Overview').classes('font-bold text-orange-500')

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


def show_project_info(project):
    dialog = ui.dialog()

    with dialog, ui.card():
        ui.label('Project Info').classes('font-bold text-orange-500')

        data = {
            "ID": project.id,
            "Name": project.name,
            "Description": project.description,
            "Database URL": project.databaseURL,
            "Kleio Server URL": project.kleioServerURL,
            "Solr Core": project.solr_core_name,
            "Created": project.created,
            "Updated": project.updated,
        }

        for key, val in data.items():
            with ui.row().classes('items-center gap-2'):
                ui.label(f"{key}:").classes('font-bold')
                ui.label(str(val))

        ui.button('Close', on_click=dialog.close)

    dialog.open()


def show_kleio_info(kserver: KleioServer):
    """Helper function to display Kleio Server Path and other variables."""
    dialog = ui.dialog()
    with dialog, ui.card():

        ui.label('Kleio Server Overview').classes('font-bold text-orange-500')
        ui.markdown(f"""
        - **Kleio URL:** {kserver.url}
        - **Kleio Home:** {kserver.kleio_home}
        """)
        ui.button('Close', on_click=dialog.close)

    dialog.open()


def load_data(query: str, database: TimelinkDatabase):

    "Retrieve all data from a specific table to display on the Explore page."

    try:

        tablename = query if query != "functions" else "relations"
        attr_table = database.get_table(tablename)

        if query == "functions":
            stmt = select(
                attr_table.c.the_value, func.count().label('count')
            ).where(attr_table.c.the_type == 'function-in-act').group_by('the_value')

            with database.session() as session:
                attr_results = session.execute(stmt)
                attr_df = pd.DataFrame(attr_results)

        else:
            stmt = select(
                attr_table.c.the_type, func.count().label('count'),
                func.count(func.distinct(attr_table.c.the_value)).label('distinct_value')
            ).group_by('the_type')

            with database.session() as session:
                attr_results = session.execute(stmt)
                attr_df = pd.DataFrame(attr_results)

        return attr_df

    except Exception as e:
        print(f"Couldn't load info from table '{tablename}': {e}")
        return None


def add_description_column(df: pd.DataFrame, database: TimelinkDatabase, id_column: str, session):
    """Add an additional description column to a given dataframe that displays information on the ID.

        Args:
            df          : Dataframe to be filled with descriptions.
            database    : The TimeLinkDatabase that contains information on the ID.
            id_column   : The column from which the description should be retrieved

    """

    df["description"] = df[id_column].apply(lambda x: str(database.get_entity(x, session=session)))

    return df


def pre_process_attributes_df(df_to_process: pd.DataFrame, attr_type: str):
    """Pre-process a dataframe to retrieved with entities_with_attributes to be displayable on an AG Grid.

        Args:
            df_to_process   : Dataframe with the information queried from entities_with_attributes
            attr_type       : the name of the attribute the table is being built for.
    """

    processed_pd = df_to_process.copy()

    processed_pd = processed_pd.drop(columns=[col for col in processed_pd.columns if col.endswith('extra_info')])

    processed_pd.columns = [c.replace('.', '_') for c in processed_pd.columns]

    col_definitions = []
    for c in processed_pd.columns:
        col_def = {'headerName': c.replace(f'{attr_type}_', '').upper(), 'field': c, 'resizable': True, 'autoHeight': True}

        if c.lower() == 'id':
            col_def['cellClass'] = 'highlight-cell'
        elif c.lower() == 'description':
            col_def.update({'wrapText': True, 'hide': True, 'minWidth': 300})
        col_definitions.append(col_def)

    return processed_pd, col_definitions


def build_expected_col_list(df: pd.DataFrame, id_field: str):
    """Convert a DataFrame into AG Grid column definitions, tagging one column as ID."""

    col_defs = []
    for col in df.columns:
        col_def = {
            'headerName': col.replace('_', ' ').title(),
            'field': col
        }
        if col == id_field:
            col_def['cellClass'] = 'highlight-cell'
        col_defs.append(col_def)
    return col_defs


def parse_entity_details(entity: Entity):
    """Parse an entity's details to display on the entity's page.

        Args:

        entity      : The entity with attributes to parse.

    """

    mr_schema = EntityAttrRelSchema.model_validate(entity)

    mr_schema_dump = mr_schema.model_dump(exclude=['contains'])

    return entity.dated_bio(), mr_schema_dump['rels_in'], mr_schema_dump['rels_out']


def format_obs(obs_text, level):
    indent = (level + 1) * 6
    return (
        f'/<span class="title-definition">obs</span>='
        f'\n<span style="display:inline-block; padding-left:{indent}ch; text-indent:0;" class="mono">'
        f'{obs_text}</span> '
    )


def highlight_link(path, text):
    return (
        "<span class='highlight-cell' onclick=\"window.location.href='" +
        path + "'\">" + text + "</span>"
    )


def collect_all_ids_sync(database, entity):
    """
    Collect all ids necessary to fill the jinja template with information.
    """
    with database.session() as session:
        childs_list = []

        def recurse(ent, level):
            act_dict = EntityAttrRelSchema.model_validate(ent).model_dump(exclude=['rels_in'])
            for item in act_dict.get("contains", []):
                child = database.get_entity(item["id"], session=session)
                if child is None:
                    continue

                child_dict = EntityAttrRelSchema.model_validate(child).model_dump(exclude=['rels_in'])
                child_dict["extra_attrs"] = {}

                for attr in child_dict.get("extra_info", {}).keys():
                    if attr != "class":
                        try:
                            kleio_class = child_dict["extra_info"].get(attr, {}).get("kleio_element_class")
                            if kleio_class:
                                child_dict["extra_attrs"][kleio_class] = getattr(child, attr, None)
                        except KeyError:
                            continue

                child_dict["extra_attrs"]["inside"] = child.inside
                child_dict["level"] = level
                childs_list.append(child_dict)
                recurse(child, level + 1)

        recurse(entity, 1)
        return childs_list


def get_entity_count_table(database: TimelinkDatabase):
    """Helper function to retrieve the count of entities currently in the database."""

    stmt = select(Entity.pom_class, func.count().label('count')).group_by(Entity.pom_class)

    with database.session() as session:
        result = session.execute(stmt)
        pom_class_df = pd.DataFrame(result, columns=['pom_class', 'count'])

    return pom_class_df


def get_recent_sources(database: TimelinkDatabase):
    """Helper function to retrieve recent sources into a dataframe."""

    imported = database.get_imported_files()

    imported_df = pd.DataFrame([dict(file) for file in imported])

    # Replace NaT columns
    imported_df["imported"] = imported_df["imported"].fillna(pd.Timestamp(0))

    return imported_df.astype({col: str for col in imported_df.select_dtypes(include=['datetime']).columns})


def get_recent_history(database: TimelinkDatabase, searched_only: bool = False):
    """Helper function to retrieve activity log as a dataframe.

        Args:
            database        :   The TimelinkDatabase we are handling currently
            searched_only   :   Boolean that defines if we are looking for recent searches or for entity logs

    """

    search_types = ["searched", "SQL search", "Name search", "Name search (exact)", "Free search"]

    if searched_only:
        condition = Activity.activity_type.in_(search_types)
    else:
        condition = ~Activity.activity_type.in_(search_types)

    with database.session() as session:
        result = session.execute(select(
            Activity.entity_id,
            Activity.entity_type,
            Activity.activity_type,
            Activity.desc,
            Activity.when
        ).where(condition))

        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df.astype({col: str for col in df.select_dtypes(include=['datetime']).columns})


if __name__ == "__main__":
    run_setup()
