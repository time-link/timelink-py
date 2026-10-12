"""Console script for timelink.

Also provides basic mhk manager functionality.

Run with  python -m timelink.cli

"""

import os
import platform
import shutil
import subprocess
from pathlib import Path

import docker
import typer
import uvicorn

from timelink import migrations, version
from timelink.api.database import (
    TimelinkDatabase,
    get_postgres_dbnames,
    get_postgres_url,
    get_sqlite_databases,
    get_sqlite_url,
)
from timelink.kleio.kleio_server import (
    is_project_directory,
    is_timelink_home_directory,
)
from timelink.mhk.utilities import get_mhk_info, is_mhk_installed

server: uvicorn.Server = None  # uvicorn server instance

# get the current directory
# this is used to find the alembic.ini file
# and the migrations folder
# ROOT_PATH = Path(__file__).parent.parent
current_working_directory = os.getcwd()

# We use Typer https://typer.tiangolo.com
app = typer.Typer(help=f"Timelink and MHK manager {version}")
mhk_app = typer.Typer()
app.add_typer(mhk_app, name="mhk", help="MHK legacy manager")
db_app = typer.Typer()
app.add_typer(db_app, name="db", help="Database manager")
create_app = typer.Typer()
app.add_typer(create_app, name="create", help="Create new project or multi project home")


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
# Project creation from template repositories
# ================================================

#: repository with the single user, single project template
PROJECT_TEMPLATE_REPO = "https://github.com/time-link/timelink-project-template.git"
#: repository with the multi project home template
HOME_TEMPLATE_REPO = "https://github.com/time-link/timelink-home-template.git"


def clone_template_repo(repo_url: str, path: Path, is_template_dir, what: str):
    """Clone a Timelink template repository into ``path``.

    Hardened version of a plain ``git clone`` of a template repository:

    * refuses to use an existing non empty directory;
    * clones with ``--depth 1``;
    * discards the template repository history and starts a fresh
      ``git init``, so the new project is not connected to the
      template repository;
    * validates the result and adds the marker file
      (``.timelink-project`` or ``.timelink-home``) if the template
      does not provide it;
    * removes the partial directory when it fails.

    Args:
        repo_url (str): url of the template repository
        path (Path): target directory, created by the clone
        is_template_dir (callable): one of
            :func:`is_project_directory` or
            :func:`is_timelink_home_directory`, used to validate
            the cloned directory
        what (str): "project" or "multi project home", used in messages
    """
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            typer.echo(
                f"Error: {path} already exists and is not an empty directory.",
                err=True,
            )
            raise typer.Exit(code=1)

    if shutil.which("git") is None:
        typer.echo(
            "Error: git is required to create a project from a template repository.",
            err=True,
        )
        raise typer.Exit(code=1)

    created = not path.exists()
    try:
        typer.echo(f"Cloning {what} template from {repo_url} into {path}")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(path)],
            check=True,
        )
        # keep the template files, discard the template repository history
        if (path / ".git").is_dir():
            shutil.rmtree(path / ".git")
        subprocess.run(["git", "init"], cwd=path, check=True)
    except (subprocess.CalledProcessError, OSError) as error:
        typer.echo(f"Error: could not create the {what} at {path}: {error}", err=True)
        if created and path.exists():
            shutil.rmtree(path)
        raise typer.Exit(code=1) from error

    # validate the cloned directory, adding the marker file if missing
    try:
        valid = is_template_dir(str(path), add_placeholder=True)
    except ValueError as error:
        typer.echo(f"Error: {error}", err=True)
        valid = False
    if not valid:
        typer.echo(
            f"Error: {path} was cloned from {repo_url}"
            f" but is not a valid Timelink {what} directory.",
            err=True,
        )
        if created and path.exists():
            shutil.rmtree(path)
        raise typer.Exit(code=1)
    typer.echo(f"Timelink {what} created at {path}")


@create_app.command("project")
def create_project(
    path: Path = typer.Argument(
        Path("timelink-project"),
        help="directory where the project is created; must not exist or be empty",
    ),
):
    """Create a new Timelink project from the timelink-project-template repository.

    The project directory associates kleio source files with a database
    and is used as timelink-home in single user, single project mode;
    it can also live inside a multi project home.
    """
    clone_template_repo(PROJECT_TEMPLATE_REPO, path, is_project_directory, "project")
    typer.echo(
        f"Next: cd {path}, create a Python environment and open "
        f"{path}/notebooks/README.md"
    )


@create_app.command("multiproject")
def create_multiproject(
    path: Path = typer.Argument(
        Path("timelink-multi-project"),
        help="directory where the home is created; must not exist or be empty",
    ),
):
    """Create a new Timelink multi project home from the timelink-home-template repository."""
    clone_template_repo(
        HOME_TEMPLATE_REPO, path, is_timelink_home_directory, "multi project home"
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
        for db in sorted(
            get_sqlite_databases(current_working_directory, relative_path=False)
        )
    ]
    all_dbs = postgres_list + sqlite_list
    if avoid_patterns:
        all_dbs = [
            db
            for db in all_dbs
            if all([pattern not in db[1] for pattern in avoid_patterns])
        ]

    # make tuples of the form (int, db info) from postgres_list + sqlite_list
    enumeration = enumerate(sorted(all_dbs, key=lambda x: x[1]), 1)
    db_index = {i: db for i, db in enumeration}
    return db_index


def parse_db_url(db_url):
    # check if db_url is an integer
    if type(db_url) is int or db_url.isdigit():
        # TODO: in the future user databases may need migration too, need to refactor
        db_index = create_db_index(
            avoid_patterns=avoid_db_patterns
        )  # this is to avoid users databases
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
        typer.echo(f" {nr - i:>3} {revision.revision[:4]} {revision.doc} <- {down[:4]}")
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

    see:
    https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.get_current_heads
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
        typer.echo("Could not find a MHK instalation")
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
