import typer
from pathlib import Path
from typing import Optional
import subprocess
import timelink
from timelink.kleio import KleioServer
import os
import psutil
import sys


app = typer.Typer()
create_app = typer.Typer()
start_app = typer.Typer()

app.add_typer(create_app, name="create")
app.add_typer(start_app, name="start")

SINGLE_PROJECT_DIRECTORY_REPO = "https://github.com/time-link/timelink-project-template.git"
MULTI_PROJECT_DIRECTORY_REPO = "https://github.com/time-link/timelink-home-template.git"
TIMELINK_ENV_PATH = Path.home() / ".timelink" / ".env"


# ----------------- TIMELINK HELPER FUNCTIONS  ------------------------- #


def run_kserver_setup(timelink_path: str, timelink_port: int, database: str):

    # Timelink Information
    local_version = timelink.version
    last_version = timelink.get_latest_version()
    typer.echo(f"Local Timelink version: {local_version}, latest Timelink version: {last_version}")

    # Timelink Home and Server
    timelink_home = os.path.normpath(KleioServer.find_local_kleio_home(path= timelink_path))
    typer.echo("Timelink Home set to: " + timelink_home)
    env_dir = TIMELINK_ENV_PATH.parent
    env_dir.mkdir(parents=True, exist_ok=True)
    kserver = KleioServer.start(kleio_home=timelink_home, kleio_external_port= str(timelink_port))
    typer.echo("Kleio Server URL: " + kserver.get_url())
    typer.echo("Kleio Server Token: " + kserver.get_token()[0:6])
    typer.echo("Kleio Server Home: " + kserver.get_kleio_home())

    typer.echo(f"Starting Timelink project at: {kserver.get_kleio_home()} on port {kserver.get_url()[-4:]}")

    with TIMELINK_ENV_PATH.open("w") as f:
        f.write(f'TIMELINK_HOME="{str(Path(timelink_home).resolve()).replace("\\", "\\\\")}"\n')
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


def is_port_in_use(port):
    """Helper function to check for usable ports."""
    for conn in psutil.net_connections(kind="inet"):
        if conn.laddr.port == port:
            typer.echo(f"Port {port} is in use already. Attempting next port over...")
            return True
    return False


def find_free_port(from_port=8088, to_port=8099):
    """Find next available port to launch the server in. This takes into account already running docker containers."""
    for port in range(from_port, to_port + 1):
        if not is_port_in_use(port):
            typer.echo(f"Port {port} will be used if no Timelink server is running.")
            return port
    raise RuntimeError(f"No free ports (up to {to_port}) found.")


@start_app.command("project")
def start_project(path: Path = Path("."), 
                  port: Optional[int] = typer.Option(None, "-p", "--port"),
                  database: Optional[str] = typer.Option("sqlite", "--database", "-d", help="Which database type to expect when launching the Web App. (Accepts sqlite, postgres)")):
    """Start a timelink docker server on defined path and port. 
        If none are given, the path defaults to current directory, and the port to the first available port after 8088
    """

    port = find_free_port(port or 8088, 8099)
    path = os.path.normpath(path.resolve() if not path.is_absolute() else path)

    if database not in ("sqlite", "postgres"):
        typer.echo(f"Warning: '{database}' is not a supported database backend. Defaulting to 'sqlite'.", err=True)
        database = "sqlite"

    run_kserver_setup(path, port, database)


# ----------------- TIMELINK WEB SETUP ------------------------- #

@start_app.command("web")
def start_webproject(
    port: Optional[int] = typer.Option(None, "-p", "--port", help="Port from which to launch the Web Application. Defaults to 8000")
    ):
    """Start the webapp on the chosen port if set. If not, read from .env file. If not, default to 8000."""
    port = port or 8000
    web_app_path = Path(__file__).parent / "web/timelink_web.py"

    typer.echo(f"Starting Timelink Web Interface at port {port}.")

    subprocess.run([sys.executable, str(web_app_path), "--port", str(port)])

if __name__ == "__main__":
    app()