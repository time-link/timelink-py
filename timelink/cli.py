"""Console script for timelink.

Also provides basic mhk manager functionality.


"""
import click
from timelink.mhk.utilities import get_mhk_env
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
    """shows MHK manager version"""
    mhk_env = get_mhk_env()
    mhk_home = mhk_env['HOST_MHK_HOME']
    with open(mhk_home + '/app/manager_version', 'r') as file:
        mv = file.readlines()
    click.echo(mv[0].replace('\n',''))
    client = docker.from_env()
    docker_version = client.version()
    print(docker_version['Platform']['Name'],docker_version['Version'])
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
