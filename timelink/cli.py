"""Console script for timelink.

Also provides basic mhk manager functionality.

Run with  python -m timelink.cli

"""

import os
import platform
import uvicorn
import typer
import docker
from timelink.mhk.utilities import get_mhk_info, is_mhk_installed
from timelink import migrations
from timelink.api.database import TimelinkDatabase, get_postgres_dbnames
from timelink.api.database import get_sqlite_databases
from timelink.api.database import get_postgres_url
from timelink.api.database import get_sqlite_url


server: uvicorn.Server = None  # uvicorn server instance

# get the current directory
# this is used to find the alembic.ini file
# and the migrations folder
# ROOT_PATH = Path(__file__).parent.parent
current_working_directory = os.getcwd()

# We use Typer https://typer.tiangolo.com
app = typer.Typer(help="Timelink and MHK manager")
mhk_app = typer.Typer()
app.add_typer(mhk_app, name="mhk", help="MHK legacy manager")
db_app = typer.Typer()
app.add_typer(db_app, name="db", help="Database manager")


# Start server
# see alternative methods
# https://github.com/miguelgrinberg/python-socketio/issues/332#issuecomment-712928157
# https://stackoverflow.com/questions/68603658/how-to-terminate-a-uvicorn-fastapi-application-cleanly-with-workers-2-when


def cli_header():
    typer.echo("Timelink and MHK manager")
    typer.echo(f"{current_working_directory}")


@app.command("start")
def start():
    """Starts timelink with uvicorn"""
    typer.echo("Starting Timelink")
    config = uvicorn.Config("timelink.app.main:app", port=8008, reload=True)

    global server  # pylint: disable=global-statement
    server = uvicorn.Server(config)
    server.run()
    return 0


# ================================================
# DB related commands
# These are used to manage the database migrations
# ================================================


db_index = {}
db_url = {}
avoid_db_patterns = ["_users"]


def create_db_index(avoid_patterns=None):
    """Create a dictionary of databases

    Args:
        avoid_patterns (list): list of patterns to avoid in the database name

    Returns:
        dict: dictionary of databases, key is an integer,
                    value is a tuple of the form:
                    (db_type, db_name, db_url)

    """
    postgres_list = [
        ("postgres", db, get_postgres_url(db)) for db in sorted(get_postgres_dbnames())
    ]
    sqlite_list = [
        ("sqlite", os.path.basename(db), get_sqlite_url(db))
        for db in sorted(get_sqlite_databases(current_working_directory, relative_path=False))
    ]
    all_dbs = postgres_list + sqlite_list
    if avoid_patterns:
        all_dbs = [db for db in all_dbs if all([pattern not in db[1] for pattern in avoid_patterns])]

    # make tuples of the form (int, db info) from postgres_list + sqlite_list
    enumeration = enumerate(sorted(all_dbs, key=lambda x: x[1]), 1)
    db_index = {i: db for i, db in enumeration}
    return db_index


def parse_db_url(db_url):
    # check if db_url is an integer
    if type(db_url) is int or db_url.isdigit():
        # TODO: in the future user databases may need migration too, need to refactor
        db_index = create_db_index(avoid_patterns=avoid_db_patterns)  # this is to avoid users databases
        key = int(db_url)
        db_url = (db_index[key])[2]
    return db_url


@db_app.command("list")
def db_database_list_cmd():
    """List all available databases (sqlite, postgresql, etc)"""
    global db_index
    db_index = create_db_index(avoid_patterns=avoid_db_patterns)
    typer.echo("Available data bases:")
    for i, db in db_index.items():
        db_url = db[2]
        db_version = migrations.heads(db_url)
        if len(db_version) == 0:
            db_version = ''
        else:
            db_version = f" ({db_version[0][:4]})"
        typer.echo(f" {i:>6}{db[0]:>9} {db_version:>8} {db[1]}: {db_url}")  # f-string
    typer.echo("\nList of revisions:")
    revisions = migrations.get_versions()
    for revision in revisions:
        down = revision.down_revision or "None"
        typer.echo(f" {revision.revision[:4]} {revision.doc} <- {down[:4]}")
    return db_index


@db_app.command("current")
def db_current_cmd(
    db_url: str,
    verbose: str = "--verbose",
):
    """Display current database revision"""
    db_url = parse_db_url(db_url)

    migrations.current(db_url, verbose)


@db_app.command("upgrade")
def db_upgrade_cmd(db_url: str, revision: str = "heads"):
    """Update database to (most recent) revision

    """
    db_url = parse_db_url(db_url)
    TimelinkDatabase(db_url=db_url)
    migrations.upgrade(db_url, revision)
    typer.echo(f"Database {db_url} upgraded to revision {revision}")


@db_app.command("create")
def db_create_cmd(db_url: str = typer.Argument(..., help="Database URL")):  # noqa: B008
    """Create a new database"""
    TimelinkDatabase(db_url=db_url)
    typer.echo(f"Database {db_url} created")


@db_app.command("heads")
def db_heads(db_url: str):
    """Return the head(s) (current revision)

    see: https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.get_current_heads
    """
    db_url = parse_db_url(db_url)
    typer.echo(migrations.heads(db_url))


@db_app.command("revision")
def db_revision(db_url: str, message: str):
    """Create a new migration script"""
    db_url = parse_db_url(db_url)
    migrations.revision(db_url, message)


@db_app.command("autogenerate")
def db_autogenerate(db_url: str, message: str):
    """Create a new migration script"""
    db_url = parse_db_url(db_url)
    migrations.autogenerate(db_url, message)


@db_app.command("history")
def db_history(verbose: bool = False):
    """Show the migration history"""
    migrations.history(verbose)


@db_app.command("stamp")
def db_stamp(db_url: str, revision: str):
    """Stamp the database to a given revision. Use 'heads' to mark the database as up-to-date"""
    db_url = parse_db_url(db_url)
    migrations.stamp(db_url, revision)

# ====================
# MHK related commands
# ====================


@mhk_app.command(name="version")
def mhk_version():
    """shows MHK manager version

    Demonstrates how to access MHK installation files and
    usage of Docker API
    """
    if is_mhk_installed():
        mhk_info = get_mhk_info()

        try:
            client = docker.from_env(version="auto")
            dv = client.version()
            mhkv = f"""    Manager version:  {mhk_info.mhk_version}
            Docker version:   {dv["Version"]}
            Host OS:          {platform.system()} {platform.release()}
            User home:        {mhk_info.user_home}
            mhk-home:         {mhk_info.mhk_home}
            mhk-home init:    {mhk_info.mhk_home_init}
            mhk-home update:  {mhk_info.mhk_home_update}
            mhk use-tag:      {mhk_info.mhk_app_env.get("TAG", "*none*")}
            mhk local host:   {mhk_info.mhk_host}
            MHK URL:          http://127.0.0.1:8080/mhk
            Kleio URL:        http://127.0.0.1:8088
            Portainer URL:    http://127.0.0.1:9000"""
            typer.echo(mhkv)
        except Exception as e:
            typer.echo(f"Could not access docker: {e}")
    else:
        type.echo("Could not find a MHK instalation")
    return 0


@mhk_app.command(name="status")
def mhk_status():
    """shows docker status information"""
    client = docker.from_env()
    dinfo = client.info()
    typer.echo(
        f"""
    Containers  :{dinfo['Containers']}
       Running  :{dinfo['ContainersRunning']}
       Paused   :{dinfo['ContainersPaused']}
       Stopped  :{dinfo['ContainersStopped']}
    """
    )
    return 0


# ================
# Main
# ================


@app.callback()
def main():
    """
    This is the timelink/MHK manager on the command line
    """

    typer.echo("This is the timelink/MHK manager")


if __name__ == "__main__":
    app()  # pragma: no cover
