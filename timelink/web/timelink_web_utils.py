from nicegui import ui
from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase, get_sqlite_databases, get_postgres_dbnames
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema
from timelink.web.models import Activity, ActivityBase
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select, func
import pandas as pd
from datetime import datetime


def run_imports_sync(db):
    print("Attempting to update database from sources...")
    db.update_from_sources(match_path= True)
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



async def run_setup():
    """ Load configuration environment variables, connect to kleio server and make the database."""

    # Load Kleio configuration from the environment.
    load_dotenv(Path.home() / ".timelink" / ".env")
    timelink_url = os.getenv('TIMELINK_SERVER_URL')
    timelink_token = os.getenv('TIMELINK_SERVER_TOKEN')
    timelink_home  = os.getenv('TIMELINK_HOME')
    db_type  = os.getenv('TIMELINK_DB_TYPE')

    # Attach to server.
    kserver = KleioServer.start(kleio_admin_token= timelink_token, kleio_home= timelink_home)

    print(f"Connected to Kleio Server at {timelink_url}, home is {timelink_home}")

    # Database setup
    db = run_db_setup(timelink_home, db_type)
    db.set_kleio_server(kserver)


    return kserver, db


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
    with dialog, ui.card() as card:

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
            stmt = select(attr_table.c.the_value, func.count().label('count')
                            ).where(attr_table.c.the_type=='function-in-act').group_by('the_value')
            
            with database.session() as session:
                attr_results = session.execute(stmt)
                attr_df = pd.DataFrame(attr_results)

        else:
            stmt = select(attr_table.c.the_type, func.count().label('count'),
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



def format_date(raw):
    """Format date dynamically according to a raw date input string"""

    raw = str(raw)
    if len(raw) == 8:
        year = raw[:4]
        month = raw[4:6]
        day = raw[6:8]
        return f"{year}-{month}-{day}"
    elif len(raw) == 6:
        year = raw[:4]
        month = raw[4:6]
        return f"{year}-{month}-01"
    elif len(raw) == 4:
        return f"{raw}-01-01"
    elif len(raw) == 10:
        return raw
    else:
        return "0001-01-01"
    

def parse_flexible_date(date_str, default = "0001-01-01"):
    """Parses a date in YYYY, YYYY-MM, or YYYY-MM-DD format.
       Returns a datetime.date or the default if invalid."""
    
    if not date_str:
        return default

    formats = ["%Y", "%Y-%m", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return str(datetime.strptime(date_str, fmt).date())
        except ValueError:
            continue
    return default


def format_obs(obs_text, level):
    indent = (level + 1) * 6
    return (
        f'/<span class="title-definition">obs</span>='
        f'\n<span style="display:inline-block; padding-left:{indent}ch; text-indent:0;" class="mono">'
        f'{obs_text}</span> '
    )

def highlight_link(path, text):
    return f"<span class='highlight-cell' onclick=\"window.location.href='{path}'\">{text}</span>"


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
            ).where(condition)
        )
        df = pd.DataFrame(result.fetchall(), columns=result.keys())

    return df.astype({col: str for col in df.select_dtypes(include=['datetime']).columns})


if __name__ == "__main__":
    run_setup()