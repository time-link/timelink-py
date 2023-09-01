""" Interface to Kleio server"""
import os
import docker
import secrets


def is_kserver_running():
    """Check if kleio server is running in docker"""
    client = docker.from_env()

    containers: list[
        docker.models.containers.Container
    ] = client.containers.list(filters={"ancestor": "timelinkserver/kleio-server"})
    if len(containers) == 0:  # check for kleio-server as part of a MHK instalation (different image)
        containers = client.containers.list(filters={"ancestor": "joaquimrcarvalho/kleio-server"})

    return len(containers) > 0

def get_kserver_container() -> docker.models.containers.Container:
    """Get the Kleio server container
    Returns:
        docker.models.containers.Container: the Kleio server container
    """

    client: docker.DockerClient = docker.from_env()
    containers: list[
        docker.models.containers.Container
    ] = client.containers.list(filters={"ancestor": "timelinkserver/kleio-server"})
    if len(containers) == 0:  # check for kleio-server as part of a MHK instalation (different image)
        containers = client.containers.list(filters={"ancestor": "joaquimrcarvalho/kleio-server"})
    if len(containers) > 0:    
        return containers[0]
    else:
        return None


def get_kserver_token() -> str:
    """Get the Kleio server container admin token
    Returns:
        str: the kleio server container token
    """
    if is_kserver_running():
        container = get_kserver_container()
        token = [
            env
            for env in container.attrs["Config"]["Env"]
            if env.startswith("KLEIO_ADMIN_TOKEN")
        ][0].split("=")[1]
        return token


def start_kleio_server(
        image:str = "timelinkserver/kleio-server",
        version: str | None = "latest",
        kleio_home: str | None = None,
        token: str | None = None,
):
    """Starts a kleio server in docker
    Args:
        image (str, optional): kleio server image. Defaults to "time-link/kleio-server".
        version (str | None, optional): postgres version. Defaults to "latest".
        kleio_home (str | None, optional): kleio home directory. Defaults to None -> current directory.
        token (str | None, optional): kleio server token. Defaults to None -> generate a random token.

    TODO: if token is None, get a token from the environment
    """
    # check if kleio server is already running in docker
    if is_kserver_running():
        return get_kserver_container()

    # if kleio_home is None, use current directory
    if kleio_home is None:
        kleio_home = os.getcwd()

    if token is None:
        token = gen_token()

    client = docker.from_env()
    kleio_container = client.containers.run(
                                image=f"{image}:{version}",
                                detach=True,
                                ports={"8088/tcp": 8088},
                                environment={
                                    "KLEIO_ADMIN_TOKEN": token,
                                    # TODO ports, workers and DEBUG
                                },
                                volumes={kleio_home: {"bind": "/kleio-home", "mode": "rw"}},
                            )
    kleio_container.start()  # redundant?
    return kleio_container

def gen_token():
    # get token from environment
    token = os.environ.get("KLEIO_ADMIN_TOKEN")
    if token is None:
        token = random_token()
        os.environ["KLEIO_ADMIN_TOKEN"] = token
    return token

def random_token(length=32):
    """Generate a random token"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for i in range(length))