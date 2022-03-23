"""Console script for timelink.

Also provides basic mhk manager functionality.

TODO consider typer https://typer.tiangolo.com

"""
import typer
import platform
from timelink.mhk.utilities import get_mhk_env, get_mhk_app_env
import docker

# We use Typer https://typer.tiangolo.com

app = typer.Typer(help="Timelink and MHK manager")
mhk_app = typer.Typer()
app.add_typer(mhk_app, name="mhk", help="MHK legacy manager")


@mhk_app.command(name='version')
def mhk_version():
    """shows MHK manager version

    Demonstrates how to access MHK installation files and
    usage of Docker API
    """

    # this should go to mhk.utilities as get_mhk_info()
    mhk_env = get_mhk_env()
    user_home = mhk_env['HOST_MHK_USER_HOME']
    mhk_home = mhk_env['HOST_MHK_HOME']
    with open(mhk_home + '/app/manager_version', 'r') as file:
        mv = file.read().replace('\n', '')
    with open(mhk_home + '/.mhk-home', 'r') as file:
        mhk_home_update = file.read().replace('\n', '')
    with open(mhk_home + '/.mhk-home-manager-init', 'r') as file:
        mhk_home_init = file.read().replace('\n', '')

    mhk_app_env = get_mhk_app_env()
    mhk_host = mhk_app_env.get('MHK_HOST', 'localhost')
    # end of get_hmk_info

    client = docker.from_env()
    dv = client.version()
    mhkv = \
        f"""    Manager version:  {mv}
    Docker version:   {dv["Version"]}
    Host OS:          {platform.system()} {platform.release()}
    User home:        {user_home}
    mhk-home:         {mhk_home}
    mhk-home init:    {mhk_home_init}
    mhk-home update:  {mhk_home_update}
    mhk use-tag:      {mhk_app_env.get("TAG", "*none*")}
    mhk local host:   {mhk_host}
    MHK URL:          http://127.0.0.1:8080/mhk
    Kleio URL:        http://127.0.0.1:8088
    Portainer URL:    http://127.0.0.1:9000"""
    typer.echo(mhkv)
    return 0


@mhk_app.command(name='status')
def mhk_status():
    """shows docker status information"""
    client = docker.from_env()
    dinfo = client.info()
    typer.echo(f"""
    Containers  :{dinfo['Containers']}
       Running  :{dinfo['ContainersRunning']}
       Paused   :{dinfo['ContainersPaused']}
       Stopped  :{dinfo['ContainersStopped']}
    """)
    return 0


@app.callback()
def main():
    """
     This is the timelink/MHK manager on the command line
     """

    typer.echo("This is the timelink/MHK manager on the command line")


if __name__ == "__main__":
    app()  # pragma: no cover
