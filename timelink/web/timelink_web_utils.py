from nicegui import ui
from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase, get_sqlite_databases, get_postgres_dbnames
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from timelink.web.models import Activity, ActivityBase
from timelink.web.backend.solr_wrapper import SolrWrapper
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select, func
import pandas as pd
import docker
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, date
import json


def run_imports_sync(db):
    print("Attempting to update database from sources...")
    db.update_from_sources(match_path=True)
    print("Database successfully updated!")


def run_db_setup(khome, db_type):

    print("Selected Database configuration:", db_type)

    if db_type == "sqlite":
        db_dir = os.path.join(khome, 'database', 'sqlite')
        print("Database type is set to Sqlite.")
        print("Databases will reside in: ", db_dir)
        print("Databases found in directory: ", get_sqlite_databases(directory_path=khome))

        db = TimelinkDatabase(db_type=db_type, db_path=db_dir, db_name='timelink-web')
    elif db_type == "postgres":

        print("Database type is set to Postgres.")
        print("Databases found in directory: ", get_postgres_dbnames())

        db = TimelinkDatabase(db_type='postgres', db_name='timelink-web')

    # Check if activity table exists here, and if not, create it for logging purposes
    tables = db.db_table_names()

    if "activity" not in tables:
        print("No Activity table found in the database - creating one.")
        ActivityBase.metadata.create_all(bind=db.engine, tables=[Activity.__table__])

    return db


def is_port_in_use_docker(port: int) -> bool:
    client = docker.from_env()
    for c in client.containers.list():
        ports = c.attrs["NetworkSettings"]["Ports"]
        if ports:
            for _, mappings in ports.items():
                if mappings:
                    for m in mappings:
                        if int(m["HostPort"]) == port:
                            return True
    return False


def find_free_port(from_port: int = 8088, to_port: int = 8099):
    for port in range(from_port, to_port + 1):
        if not is_port_in_use_docker(port):
            return port
    raise OSError(f"No free ports available in {from_port}-{to_port}")


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


def json_serial(obj):
    """JSON serializer for datetime objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def flatten_dictionary(data, parent_key='', sep='_'):
    """Flatten a dictionary to be received by Solr"""
    items = {}

    for k, v in data.items():
        new_key = parent_key + sep + k if parent_key else k

        if isinstance(v, dict):
            # Recurse into nested dictionaries
            items.update(flatten_dictionary(v, new_key, sep=sep))
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, (dict, list)):
                    items.update(flatten_dictionary({str(i): item}, new_key, sep=sep))
                else:
                    items[new_key] = v
                    break
        else:
            items[new_key] = v

    # Ensure the 'id' field remains at the top level
    if 'id' in data and not parent_key:
        items['id'] = data['id']

    return items


async def init_index_job_scheduler(solr_client, database):
    """Initiate the job to index new documents to the Apache Solr database

    NOT WORKING AT THE MOMENT
    """

    ignore_classes = ['class', 'rentity', 'source']
    solr_client.delete(q='*:*', commit=True)

    with database.session() as session:
        entities = session.query(Entity).filter(Entity.indexed.is_(None)).filter(~Entity.pom_class.in_(ignore_classes)).limit(10).all()

        if not entities:
            return

        # solr_doc_list = []
        for entity in entities:
            mr_schema = EntityAttrRelSchema.model_validate(entity)
            mr_schema_dump = mr_schema.model_dump(exclude=["contains", "extra_info"])
            flattened_schema = flatten_dictionary(json.loads(json.dumps(mr_schema_dump, default=json_serial)))
            # print(flattened_schema)
            solr_client.add([flattened_schema], commit=True)
            # solr_doc_list.append(json.loads(json.dumps(mr_schema_dump, default=json_serial)))
            break

        """
        solr_client.add(solr_doc_list, commit=True)

        now = datetime.now()
        for entity in entities:
            entity.indexed = now

        session.commit()
    print("Yes!")
    """


async def run_setup(home_path: Path, job_scheduler: AsyncIOScheduler, database_type: str = "sqlite"):
    """ Load configuration environment variables, connect to kleio server and make the database."""

    timelink_home = None

    # Find timelink home in the current path.
    timelink_home = KleioServer.find_local_kleio_home(str(home_path))

    print(f"Timelink Home set to {timelink_home}")

    # If for some reason timelink home wasn't found, then attempt to read it from .timelink\.env found at root directory.
    if not timelink_home:
        print("Could not find timelink home in the current directory. Attempting to read from .timelink env options.")
        load_dotenv(Path.home() / ".timelink" / ".env")
        timelink_token = os.getenv('TIMELINK_SERVER_TOKEN')
        timelink_home = os.getenv('TIMELINK_HOME')
        db_type = os.getenv('TIMELINK_DB_TYPE')
        kserver = KleioServer.start(kleio_admin_token=timelink_token, kleio_home=timelink_home)

    else:
        kserver = KleioServer.get_server(timelink_home)
        if not kserver:
            port = find_free_port(8088, 8099)
            kserver = KleioServer.start(kleio_home=timelink_home, kleio_external_port=port)
        db_type = database_type

    # Solr setup
    solr_manager = run_solr_client_setup()

    print(f"Connected to Kleio Server at {kserver.url}, home is {kserver.kleio_home}")

    # Database setup
    db = run_db_setup(timelink_home, db_type)
    db.set_kleio_server(kserver)

    # Schedule Solr server updates (Needs update on indexing)
    # job_scheduler.add_job(init_index_job_scheduler, args = [solr_client, db], name="Index Documents to Solr", trigger="interval", seconds=10)
    # await init_index_job_scheduler(solr_client, db)

    return kserver, db, solr_manager


def show_table(database: TimelinkDatabase):
    """Helper function to display database."""
    dialog = ui.dialog()
    with dialog, ui.card():
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


def show_kleio_info(kserver: KleioServer):
    """Helper function to display Kleio Server Path and other variables."""
    dialog = ui.dialog()
    with dialog, ui.card():

        ui.label('Kleio Server Overview')
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

    search_types = ["searched", "SQL search", "Name search", "Name search (exact)"]

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
