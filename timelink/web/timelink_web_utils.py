import timelink
from timelink.kleio import KleioServer
from timelink.api.database import TimelinkDatabase, get_sqlite_databases, get_postgres_dbnames
import os, asyncio
import logging

logging.basicConfig(level=logging.INFO)

def run_imports_sync(db):
    db.update_from_sources()

async def run_imports_async(db):
    await asyncio.to_thread(run_imports_sync, db)


def run_kserver_setup():

    # Timelink Information
    local_version = timelink.version
    last_version = timelink.get_latest_version()
    print(f"Local version {local_version}, last version {last_version}")

    # Timelink Home and Server
    timelink_home = os.path.normpath(KleioServer.find_local_kleio_home())
    print("Timelink Home set to: " + timelink_home)
    kserver = KleioServer.start(kleio_home=timelink_home)
    print("Kleio Server URL: " + kserver.get_url())
    print("Kleio Server Token: " + kserver.get_token()[0:6])
    print("Kleio Server Home: " + kserver.get_kleio_home())

    return kserver, timelink_home

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

        db = TimelinkDatabase(db_type='postgres',
                                db_name='timelink-web')


    return db



def run_setup():

    # KServer setup
    kserver, timelink_home = run_kserver_setup()

    # Database setup
    db = run_db_setup(timelink_home, os.getenv('DB_TYPE', 'sqlite'))

    # Update database from sources in the background (disabled for now)
    # asyncio.create_task(run_imports_async(db))

    return kserver, db


if __name__ == "__main__":
    run_setup()