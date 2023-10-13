""" Interface to Kleio server"""
import logging
import os
import docker
import secrets
import requests
from jsonrpcclient import request, Error, Ok, parse 
from .schemas import KleioFile, TokenInfo

class KleioServer:
    url: str
    token: str

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token


    def call(self, method:str, params:dict):
        """Call kleio server API"""

        url = f"{self.url}/json/"
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {self.token}"}
        # we add the token to the params
        params["token"] = self.token
        rpc=request(method, params=params)
        response = requests.post(url,json=rpc,
                                    headers=headers )
        parsed = parse(response.json())
        if isinstance(parsed, Ok):
            return parsed.result
        elif isinstance(parsed, Error):
            code, message, data, id = parsed
            raise Exception(f"Error {code}: {message} ({data} id:{id})")
        return response
    
    def invalidate_user(self, user:str):
        """Invalidate a user"""    
        pars={"user": user}  
        return self.call("users_invalidate", pars)


    def generate_token(self, user:str,info: TokenInfo):
        """Generate a token for a user"""
        pars={"user": user, "info": info.model_dump()}  
        return self.call("tokens_generate", pars)
    

    def translation_status(self,
                           path:str, 
                           recurse:str, 
                           status:str):
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
            pars={"path": path, "recurse": recurse}  
        else:
            pars={"path": path, "recurse": recurse, "status": status}  
        translations = self.call("translations_get", pars)
        result = []
        for t in translations:
            kfile = KleioFile(**t)
            result.append(kfile)
        return result
    
    def translate(self, path:str, recurse:str, spawn:str):
        """Translate sources from kleio server
        
        Args:
            path (str): path to the directory in sources
            recurse (str): if "yes" recurse in subdirectories
            spawn (str): if "yes" spawn a translation process for each file"""
        
        pars={"path": path}  
        if recurse is not None:
            pars["recurse"] = recurse
        if spawn is not None:
            pars["spawn"] = spawn
            
        return self.call("translations_translate", pars)


    def translation_clean(self, path:str, recurse:str):
        """clean translations from kleio server

        Removes translation results from kleio server.
        
        Args:
            path (str): path to the directory in sources
            recurse (str): if "yes" recurse in subdirectories
        """
        pars={"path": path, "recurse": recurse}  
        return self.call("translations_delete", pars)


    def get_sources(self, path:str, recurse:str):
        """Get sources from kleio server"""
        pars={"path": path, "recurse": recurse}  
        return self.call("sources_get", pars)


def find_local_kleio_home(path:str=None):
    """Find kleio home directory in the current directory, parent directory, or tests directory.
    
    Kleio home directory is the directory where kleio server is running.
    It can be in the current directory, parent directory, or tests directory.
    It can be named "kleio-home", "timelink-home", or "mhk-home".
    
    """
    kleio_home = None
    if path is None:
        # get the current directory
        current_dir = os.getcwd()
    else:
        current_dir = path

    # get the user home directory
    user_home = os.path.expanduser("~")

    # check if kleio-home exists in current directory, parent directory, or tests directory
    for dir_path in [current_dir, os.path.dirname(current_dir), f"{current_dir}/tests", user_home]:
        for home_dir in ["kleio-home", "timelink-home", "mhk-home"]:
            if os.path.isdir(f"{dir_path}/{home_dir}"):
                kleio_home = f"{dir_path}/{home_dir}"
                break
        if kleio_home:
            break
    return kleio_home


def get_kserver_home():
    """Get the kleio server home directory
    
    Returns the volume mapped to /kleio-home in the kleio server container"""
    if is_kserver_running():
        container = get_kserver_container()
        kleio_home_mount = [mount['Source'] for mount in container.attrs["Mounts"] if mount['Destination'] == '/kleio-home']
        if len(kleio_home_mount) > 0:
            kleio_home = kleio_home_mount[0]
        else:
            kleio_home = None
    return kleio_home


def is_kserver_running():
    """Check if kleio server is running in docker"""
    client = docker.from_env()

    containers: list[
        docker.models.containers.Container
    ] = client.containers.list(filters={"ancestor": "timelinkserver/kleio-server"})
    if len(containers) == 0:  # check for kleio-server as part of a MHK instalation (different image)
        containers = client.containers.list(filters={"ancestor": "joaquimrcarvalho/kleio-server"})
    if len(containers) == 0:  # check for kleio-server as standalone local image
        containers = client.containers.list(filters={"ancestor": "kleio-server"})

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
    if len(containers) == 0:  # check for kleio-server as standalone local image
        containers = client.containers.list(filters={"ancestor": "kleio-server"})
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
        consistency: str = "cached",
        update: bool = False,
):
    """Starts a kleio server in docker
    Args:
        image (str, optional): kleio server image. Defaults to "time-link/kleio-server".
        version (str | None, optional): kleio-server version. Defaults to "latest".
        kleio_home (str | None, optional): kleio home directory. Defaults to None -> current directory.
        token (str | None, optional): kleio server token. Defaults to None -> generate a random token.
        update (bool, optional): update kleio server image. Defaults to False.

    """
    # check if kleio server is already running in docker
    if is_kserver_running():
        return get_kserver_container()

    # if kleio_home is None, use current directory
    if kleio_home is None:
        kleio_home = os.getcwd()
    else:
        kleio_home = os.path.abspath(kleio_home)
        os.makedirs(kleio_home, exist_ok=True)

    # ensure that kleio_home/system/conf/kleio exists
    os.makedirs(f"{kleio_home}/system/conf/kleio", exist_ok=True)

    if token is None:
        token = gen_token()

    client = docker.from_env()

    if update:
        logging.info(f"Pulling {image}:{version}")
        client.images.pull(f"{image}:{version}")


    kleio_container = client.containers.run(
                                image=f"{image}:{version}",
                                detach=True,
                                ports={"8088/tcp": 8088},
                                environment={
                                    "KLEIO_ADMIN_TOKEN": token,
                                    # TODO ports, workers and DEBUG
                                },
                                mounts=[
                                    docker.types.Mount(
                                        target="/kleio-home",
                                        source=kleio_home,
                                        type="bind",
                                        read_only=False,
                                        consistency=consistency,
                                    )
                                ],
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
    
