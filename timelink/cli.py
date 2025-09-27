"""Console script for timelink.

Provides basic mhk manager functionality, setup and launch of timelink projects, and launch point for the webapp.

Run with  python -m timelink.cli

"""

import os
import platform
import typer
import docker
from pathlib import Path
from typing import Optional
import subprocess
import sys
import socket
from sys import platform
import timelink
from timelink.mhk.utilities import get_mhk_info, is_mhk_installed
from timelink import migrations
from timelink import version
from timelink.api.database import TimelinkDatabase, get_postgres_dbnames
from timelink.api.database import get_sqlite_databases
from timelink.api.database import get_postgres_url
from timelink.api.database import get_sqlite_url
from timelink.kleio import KleioServer
from timelink.kleio.kleio_server import find_free_port


# get the current directory
# this is used to find the alembic.ini file
# and the migrations folder
# ROOT_PATH = Path(__file__).parent.parent
current_working_directory = os.getcwd()
SINGLE_PROJECT_DIRECTORY_REPO = "https://github.com/time-link/timelink-project-template.git"
MULTI_PROJECT_DIRECTORY_REPO = "https://github.com/time-link/timelink-home-template.git"
TIMELINK_ENV_PATH = Path.home() / ".timelink" / ".env"

# We use Typer https://typer.tiangolo.com
app = typer.Typer(help=f"Timelink and MHK manager {version}")
mhk_app = typer.Typer()
app.add_typer(mhk_app, name="mhk", help="MHK legacy manager")
db_app = typer.Typer()
app.add_typer(db_app, name="db", help="Database manager")
create_app = typer.Typer()
app.add_typer(create_app, name="create", help="Create new project")
start_app = typer.Typer()
app.add_typer(start_app, name="start", help="Initiate new project, or the web interface.")


def cli_header():
    typer.echo("Timelink and MHK manager")
    typer.echo(f"{current_working_directory}")


# ================================================
# Project setup related commands
# These are used to create and setup the environment for a timelinkk project.
# ================================================


def run_kserver_setup(timelink_path: str, timelink_port: int, database: str):

    # Timelink Information
    local_version = timelink.version
    last_version = timelink.get_latest_version()
    typer.echo(f"Local Timelink version: {local_version}, latest Timelink version: {last_version}")

    # Timelink Home and Server
    timelink_home = os.path.normpath(KleioServer.find_local_kleio_home(path=timelink_path))
    typer.echo("Timelink Home set to: " + timelink_home)
    env_dir = TIMELINK_ENV_PATH.parent
    env_dir.mkdir(parents=True, exist_ok=True)
    kserver = KleioServer.start(kleio_home=timelink_home, kleio_external_port=str(timelink_port))
    typer.echo("Kleio Server URL: " + kserver.get_url())
    typer.echo("Kleio Server Token: " + kserver.get_token()[0:6])
    typer.echo("Kleio Server Home: " + kserver.get_kleio_home())

    typer.echo(f"Starting Timelink project at: {kserver.get_kleio_home()} on port {kserver.get_url()[-4:]}")

    path_str = str(Path(timelink_home).resolve())
    if platform.startswith("win"):
        path_str = path_str.replace("\\", "\\\\")

    with TIMELINK_ENV_PATH.open("w") as f:
        f.write(f'TIMELINK_HOME="{path_str}"\n')
        f.write(f'TIMELINK_SERVER_URL="{kserver.get_url()}"\n')
        f.write(f'TIMELINK_SERVER_TOKEN="{kserver.get_token()}"\n')
        f.write(f"TIMELINK_DB_TYPE={database}\n")


def run_kserver_setup(timelink_path: str, timelink_port: int, database: str):

    # Timelink Information
    local_version = timelink.version
    last_version = timelink.get_latest_version()
    typer.echo(f"Local Timelink version: {local_version}, latest Timelink version: {last_version}")

    # Timelink Home and Server
    timelink_home = os.path.normpath(KleioServer.find_local_kleio_home(path=timelink_path))
    typer.echo("Timelink Home set to: " + timelink_home)
    env_dir = TIMELINK_ENV_PATH.parent
    env_dir.mkdir(parents=True, exist_ok=True)
    kserver = KleioServer.start(kleio_home=timelink_home, kleio_external_port=str(timelink_port))
    typer.echo("Kleio Server URL: " + kserver.get_url())
    typer.echo("Kleio Server Token: " + kserver.get_token()[0:6])
    typer.echo("Kleio Server Home: " + kserver.get_kleio_home())

    typer.echo(f"Starting Timelink project at: {kserver.get_kleio_home()} on port {kserver.get_url()[-4:]}")

    path_str = str(Path(timelink_home).resolve())
    if platform.startswith("win"):
        path_str = path_str.replace("\\", "\\\\")

    with TIMELINK_ENV_PATH.open("w") as f:
        f.write(f'TIMELINK_HOME="{path_str}"\n')
        f.write(f'TIMELINK_SERVER_URL="{kserver.get_url()}"\n')
        f.write(f'TIMELINK_SERVER_TOKEN="{kserver.get_token()}"\n')
        f.write(f"TIMELINK_DB_TYPE={database}\n")


# ----------------- TIMELINK MULTI PROJECT SETUP (STUB) ------------------------- #


@create_app.command("multiproject")
def create_multiproject(path: Path = Path("timelink-multi-project")):
    typer.echo(f"Getting Timelink multi project structure at: {path}")
    typer.echo(f"Cloning Timelink project template into: {path}")
    try:
        subprocess.run(["git", "clone", MULTI_PROJECT_DIRECTORY_REPO, str(path)], check=True)
        typer.echo("File structure cloned successfully.")
    except subprocess.CalledProcessError:
        typer.echo("Failed to clone the project template.")


@start_app.command("multiproject")
def start_multiproject(path: Path = Path("."), port: Optional[int] = typer.Option(None, "-p", "--port")):
    port = port or 8000
    typer.echo(f"Starting Timelink multiproject at: {path} on port {port}")


# ----------------- TIMELINK SINGLE PROJECT SETUP ------------------------- #


@create_app.command("project")
def create_project(path: Path = Path("timelink-project")):
    typer.echo(f"Getting Timelink single project structure at: {path}")
    typer.echo(f"Cloning Timelink project template into: {path}")
    try:
        subprocess.run(["git", "clone", SINGLE_PROJECT_DIRECTORY_REPO, str(path)], check=True)
        typer.echo("File structure cloned successfully.")
    except subprocess.CalledProcessError:
        typer.echo("Failed to clone the project template.")


# ================================================
# Startup related commands
# These are used to configure and launch a timelink project on a set directory, or launch the webapp.
# ================================================


@start_app.command("project")
def start_project(
    path: Path = Path("."),
    port: Optional[int] = typer.Option(None, "-p", "--port"),
    database: Optional[str] = typer.Option(
        "sqlite",
        "--database",
        "-d",
        help="Which database type to expect when launching the Web App. (Accepts sqlite, postgres)",
    ),
):
    """Start a timelink docker server on defined path and port.
    If none are given, the path defaults to current directory, and the port to the first available port after 8088
    """

    port = find_free_port(from_port=port or 8088, to_port=8099)

    path = os.path.normpath(path.resolve() if not path.is_absolute() else path)
    typer.echo(f"Starting Timelink project at: {path} on port {port}")
    if database not in ("sqlite", "postgres"):
        typer.echo(f"Warning: '{database}' is not a supported database backend. Defaulting to 'sqlite'.", err=True)
        database = "sqlite"

    run_kserver_setup(path, port, database)


def find_website_port(from_port: int = 8088, to_port: int = 8099):
    for port in range(from_port, to_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                typer.echo(f"Attempting to initialize on port {port}...")
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                pass
    raise OSError(f"No free ports available in the range {from_port}-{to_port}")


def setup_solr_container():
    """Startup the solr container. For now this assumes we already have a solr docker image ready to go."""

    solr_container_name = "solr_timelink"
    typer.echo("Checking for Solr container...")

    # Check if container is already running.
    container_running_check = subprocess.run(
        ["docker", "ps", "-f", f"name={solr_container_name}", "--format", "{{.Names}}"], capture_output=True, text=True
    )
    if solr_container_name in container_running_check.stdout:
        typer.echo(f"Solr container '{solr_container_name}' is already running.")
    else:
        # Container exists but is stopped.
        container_exists_check = subprocess.run(
            ["docker", "ps", "-a", "-f", f"name={solr_container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
        if solr_container_name in container_exists_check.stdout:
            # Container exists
            typer.echo(f"Starting existing Solr container '{solr_container_name}'...")
            subprocess.run(["docker", "start", solr_container_name], check=True)
        else:
            # Container does not exist
            typer.echo(f"Creating and starting new Solr container '{solr_container_name}'...")
            subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "-v",
                    f"{os.getcwd()}/solrdata:/var/solr",
                    "-p",
                    "8983:8983",
                    "--name",
                    solr_container_name,
                    "solr:slim",
                    "solr-create",
                    "-c",
                    "timelink-core",
                ],
                check=True,
            )


@start_app.command("web")
def start_webproject(
    port: Optional[int] = typer.Option(
        None, "-p", "--port", help="Port from which to launch the Web Application. Defaults to 8000"
    ),
    path: Optional[Path] = typer.Option(
        None, "-d", "--directory", help="Timelink project directory. Defaults to the current one."
    ),
    database: Optional[str] = typer.Option(
        "sqlite",
        "--database",
        "-db",
        help="Which database type to expect when launching the Web App. (Accepts sqlite, postgres)",
    ),
):
    """Start the webapp on the chosen port if set. If not, default to 8000."""

    setup_solr_container()
    port = find_website_port(from_port=port or 8000, to_port=8020)

    web_app_path = Path(__file__).parent / "web/timelink_web.py"

    path_to_use = path or Path.cwd()

    if database not in ("sqlite", "postgres"):
        typer.echo(f"Warning: '{database}' is not a supported database backend. Defaulting to 'sqlite'.", err=True)
        database = "sqlite"

    typer.echo(f"Starting Timelink Web Interface at port {port} on {path_to_use}.")

    subprocess.run(
        [
            sys.executable,
            str(web_app_path),
            "--port",
            str(port),
            "--directory",
            str(path_to_use),
            "--database",
            database,
        ]
    )


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
    pgsql_dbs = get_postgres_dbnames()
    postgres_list = [("postgres", db, get_postgres_url(db)) for db in sorted(pgsql_dbs)]
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
            db_version = ""
        else:
            db_version = f" ({db_version[0][:4]})"
        typer.echo(f" {i:>6}{db[0]:>9} {db_version:>8} {db[1]}: {db_url}")  # f-string
    typer.echo("\nList of revisions:")
    revisions = migrations.get_versions()
    nr = len(revisions)
    for i, revision in enumerate(revisions, 0):
        down = revision.down_revision or "None"
        typer.echo(f" {nr-i:>3} {revision.revision[:4]} {revision.doc} <- {down[:4]}")
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
    """Update database to (most recent) revision"""
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
    """Create a new migration script using db_url as reference database

    The current ORM models will be compared to the database schema
    and a migration script will be generated to bring the database
    to the current state of the ORM

    A current database is kept at tests/db/reference_db/timelink_reference.sqlite


    """
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

    typer.echo(f"This is the timelink/MHK manager {version}")


if __name__ == "__main__":
    app()  # pragma: no cover
