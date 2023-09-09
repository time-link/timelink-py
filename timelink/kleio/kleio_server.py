""" Interface to Kleio server"""
import os
import docker
import secrets
import requests
from jsonrpcclient import request, Error, Ok, parse 
from .schemas import KleioFile


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

    """
    # check if kleio server is already running in docker
    if is_kserver_running():
        return get_kserver_container()

    # if kleio_home is None, use current directory
    if kleio_home is None:
        kleio_home = os.getcwd()
    else:
        os.makedirs(kleio_home, exist_ok=True)

    # ensure that kleio_home/system/conf/kleio exists
    os.makedirs(f"{kleio_home}/system/conf/kleio", exist_ok=True)

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

def stop_kleio_server():
    """Stop kleio server"""
    if is_kserver_running():
        container = get_kserver_container()
        container.stop()
        container.remove()

def kleio_get_url():
    """Get the url of the kleio server"""
    if is_kserver_running():
        container = get_kserver_container()
        return f"http://localhost:{container.attrs['NetworkSettings']['Ports']['8088/tcp'][0]['HostPort']}"
    else:
        return None
    
def kleio_call_api(method:str, params:dict, url:str):
    """Call kleio server API"""
    if url is None and is_kserver_running():
        url = kleio_get_url()
        url = f"{url}/json/"
    else:
        url = f"{url}/json/"
    rpc=request(method, params=params)
    response = requests.post(url,json=rpc,
                                headers={"Content-Type": "application/json"}, )
    parsed = parse(response.json())
    if isinstance(parsed, Ok):
        return parsed.result
    elif isinstance(parsed, Error):
        code, message, data, id = parsed
        raise Exception(f"Error {code}: {message} ({data} id:{id})")
    return response
    
def kleio_invalidate_user(user:str, token:str, url:str):
    """Invalidate a user"""    
    pars={"user": user, "token": token}  
    return kleio_call_api("users_invalidate", pars, url)


def kleio_tokens_generate(user:str,info: dict, token:str, url:str):
    """Generate a token for a user"""
    pars={"user": user, "info": info, "token": token}  
    return kleio_call_api("tokens_generate", pars, url)
    

def kleio_translations_get(path:str, recurse:str, status:str, token:str, url:str = "http://localhost:8088/json/"):
    """Get translations from kleio server
    
    Args:
        path (str): path to the directory in sources
        recurse (str): if "yes" recurse in subdirectories
        status (str): filter by translation status
                        V = valid translations
                        T = need translation (source more recent than translation)
                        E = translation with errors
                        W = translation with warnings
                        P = translation being processed
                        Q = file queued for translation
        token (str): kleio server token
    """
    if status is None:
        pars={"path": path, "recurse": recurse, "token": token}  
    else:
        pars={"path": path, "recurse": recurse, "status": status, "token": token}  
    translations = kleio_call_api("translations_get", pars, url)
    result = []
    for t in translations:
        kfile = KleioFile(**t)
        result.append(kfile)
    return result
    

def kleio_sources_get(path:str, recurse:str, token:str, url:str):
    """Get sources from kleio server"""
    pars={"path": path, "recurse": recurse, "token": token}  
    return kleio_call_api("sources_get", pars, url)