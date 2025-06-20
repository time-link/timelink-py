from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase, get_sqlite_databases, get_postgres_dbnames
import os
from pathlib import Path
from dotenv import load_dotenv


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

if __name__ == "__main__":
    run_setup()