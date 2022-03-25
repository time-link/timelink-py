"""Console script for timelink.

Also provides basic mhk manager functionality.

"""
import typer
import platform
import docker
from timelink.mhk.utilities import get_mhk_info, is_mhk_installed

# We use Typer https://typer.tiangolo.com
app = typer.Typer(help="Timelink and MHK manager")
mhk_app = typer.Typer()
app.add_typer(mhk_app, name="mhk", help="MHK legacy manager")


@mhk_app.command(name="version")
def mhk_version():
    """shows MHK manager version

    Demonstrates how to access MHK installation files and
    usage of Docker API
    """
    if is_mhk_installed():
        mhk_info = get_mhk_info()

        client = docker.from_env()
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


@app.callback()
def main():
    """
    This is the timelink/MHK manager on the command line
    """

    typer.echo("This is the timelink/MHK manager")


if __name__ == "__main__":
    app()  # pragma: no cover
