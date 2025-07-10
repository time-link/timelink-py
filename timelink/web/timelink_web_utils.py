from nicegui import ui
from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase, get_sqlite_databases, get_postgres_dbnames
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import select, func
import pandas as pd
from timelink.api.models import Entity
from timelink.api.schemas import EntityAttrRelSchema

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


def parse_entity_details(entity: Entity):
    """Parse an entity's detailss to display on the entity's page.
    
        Args:

        entity      : The entity with attributes to parse.

    """

    mr_schema = EntityAttrRelSchema.model_validate(entity)

    mr_schema_dump = mr_schema.model_dump(exclude=['contains'])
    
    grouped = {}

    for attr in mr_schema_dump['attributes']:

        date = format_date(attr.get("the_date", "0"))
        key = attr.get("the_type", "")
        val = attr.get("the_value", "")
        obs = attr.get("obs", "")

        if date not in grouped:
            grouped[date] = []
        
        entry = {key: val}
        if obs:
            entry["obs"] = obs
        
        grouped[date].append(entry)

    return grouped, mr_schema_dump['rels_in'], mr_schema_dump['rels_out']


def format_date(raw):
    raw = str(raw)
    if len(raw) == 8:
        year = raw[:4]
        month = raw[4:6]
        day = raw[6:8]
        return f"{year}-{month}-{day}"
    elif len(raw) == 6:
        year = raw[:4]
        month = raw[4:6]
        return f"{year}-{month}-00"
    elif len(raw) == 4:
        return f"{raw}-00-00"
    else:
        return "0000-00-00"


if __name__ == "__main__":
    run_setup()