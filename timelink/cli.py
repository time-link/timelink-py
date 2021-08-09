"""Console script for timelink.

Also provides basic mhk manager functionality.

TODO consider typer https://typer.tiangolo.com

"""
import platform
import click
from timelink.mhk.utilities import get_mhk_env, get_mhk_app_env
import docker


@click.group()
def cli():
    pass


@click.group()
def mhk():
    """MHK manager commands"""
    click.echo("mhk command line interface")
    return 0


@mhk.command(name='version')
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
    print(mhkv)
    return 0


@mhk.command(name='status')
def mhk_status():
    client = docker.from_env()
    dinfo = client.info()
    print(f"""
    Containers  :{dinfo['Containers']}
       Running  :{dinfo['ContainersRunning']}
       Paused   :{dinfo['ContainersPaused']}
       Stopped  :{dinfo['ContainersStopped']}
    """)
    return 0


@click.command()
def timelink():
    """timelink command line interface"""
    click.echo("timelink cli")
    return 0


cli.add_command(mhk)
cli.add_command(timelink)

if __name__ == "__main__":
    cli()  # pragma: no cover
