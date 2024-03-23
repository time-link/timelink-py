""" Interface to Kleio Server"""

import logging
import socket
import os
from time import sleep
from typing import List, Tuple
import docker
import secrets
import requests
from jsonrpcclient import request, Error, Ok, parse
import urllib.request

from .schemas import KleioFile, TokenInfo


class KleioServerException(Exception):
    pass


class KleioServerForbidenException(KleioServerException):
    """Corresponds to json_rpc error code -32006 or HTTP 403"""

    pass


class KleioServerDockerException(KleioServerException):
    """Problem with docker"""

    pass


class KleioServer:
    """This class interfaces to a Kleio server through its JSON-RPC api.
    It also provides convenience methods
    to start a server in Docker locally.

    This class is not intended to be used directly.
    Use KleioServer.start() and KleioServer.attach() to create instances of KleioServer.

    Args:
        container (docker.models.containers.Container): runing kleio server container
        url (str): kleio server url if running in a different machine (container=None)
        token (str): kleio server token if running in a different machine (container=None)
        kleio_home (str): kleio server home directory. If None and container is not None
                            then kleio_home is obtained
                            from the container. If not none


    """

    #: kleio server host
    host: str
    #: kleio server url
    url: str
    #: kleio server admin token
    kleio_admin_token: str
    #: kleio server home directory
    kleio_home: str
    #: kleio server container
    container: docker.models.containers.Container

    @staticmethod
    def start(
        kleio_image: str = "timelinkserver/kleio-server",
        kleio_version: str | None = "latest",
        kleio_home: str | None = None,
        kleio_admin_token: str | None = None,
        kleio_server_port="8088",
        kleio_external_port=None,
        kleio_server_workers="3",
        kleio_idle_timeout=900,
        kleio_conf_dir=None,
        kleio_source_dir=None,
        kleio_stru_dir=None,
        kleio_token_db=None,
        kleio_default_stru=None,
        kleio_debug=None,
        consistency: str = "cached",
        port: int = None,
        update: bool = False,
        reuse: bool = True,
        stop_duplicates: bool = False,
    ):
        """Starts a kleio server in docker

        Args:
            kleio_image (str): kleio server image, defaults to "timelinkserver/kleio-server"
            kleio_version (str, optional): kleio-server image version, defaults to "latest"
            kleio_home (str, optional): kleio home directory,
                                        defaults to None -> current directory
            kleio_token (str, optional): kleio server admin token,
                                    defaults to None -> generate a random token
            kleio_server_port (str, optional): kleio server port (in the container),
                                                 defaults to "8088".
            kleio_external_port (str, optional): kleio server external port (in the host),
                                                    defaults to "8089".
            kleio_server_workers (str, optional): number kleio server workers, defaults to "3".
            kleio_idle_timeout (int, optional): kleio server idle timeout, defaults to 900.
            kleio_conf_dir (str, optional): kleio server configuration directory,
                                            defaults to None.
            kleio_source_dir (str, optional): kleio server sources directory,
                                            defaults to None.
            kleio_stru_dir (str, optional): kleio server structures directory,
                                            defaults to None.
            kleio_token_db (str, optional): kleio server token database,
                                            defaults to None.
            kleio_default_stru (str, optional): kleio server default structure,
                                            defaults to None.
            kleio_debug (str, optional): kleio server debug level, defaults to None.
            consistency (str, optional): consistency of the volume mount, defaults to "cached"
            port (int, optional): port to map to 8088,
                                    defaults to None -> find a free port starting at 8088
            update (bool, optional): update kleio server image, defaults to False
            reuse (bool, optional): if True, reuse an existing kleio server container
                                    with same keio_home, defaults to True.
            stop_duplicates (bool, optional): if True, stop and remove duplicate containers
                                    with same kleio_home, defaults to False.

        Returns:
            KleioServer: KleioServer object
        """
        if kleio_image is None:
            kleio_image = "timelinkserver/kleio-server"
        if kleio_version is None:
            kleio_version = "latest"
        if not is_docker_running():
            raise RuntimeError("Docker is not running")
        container: docker.models.containers.Container = start_kleio_server(
            image=kleio_image,
            version=kleio_version,
            kleio_home=kleio_home,
            kleio_admin_token=kleio_admin_token,
            kleio_server_port=kleio_server_port,
            kleio_external_port=kleio_external_port,
            kleio_server_workers=kleio_server_workers,
            kleio_idle_timeout=kleio_idle_timeout,
            kleio_conf_dir=kleio_conf_dir,
            kleio_source_dir=kleio_source_dir,
            kleio_stru_dir=kleio_stru_dir,
            kleio_token_db=kleio_token_db,
            kleio_default_stru=kleio_default_stru,
            kleio_debug=kleio_debug,
            consistency=consistency,
            update=update,
            reuse=reuse,
            stop_duplicates=stop_duplicates,
        )

        return KleioServer(container)

    @staticmethod
    def attach(url: str, token: str, kleio_home: str = None):
        """Attach to a already running Kleio Server.

        Use this either to attach to a running server
        outside docker (for instance in a Prolog session)
        or to a server running in another machine (should use
        htpps url in that case)

        Args:
            url (str): kleio server url
            token (str): kleio server token
            kleio_home (str, optional): kleio server home directory

        Returns:
            KleioServer: KleioServer object

        TODO #33:
        from urllib.parse import urlparse

        url = 'http://user:token@localhost:8088/path_to_kleio_home'
        parsed_url = urlparse(url)

        print('scheme:', parsed_url.scheme)
        print('netloc:', parsed_url.netloc)
        print('path:', parsed_url.path)
        print('username:', parsed_url.username)
        print('password:', parsed_url.password)
        print('hostname:', parsed_url.hostname)
        print('port:', parsed_url.port)

        """
        return KleioServer(url=url, token=token, kleio_home=kleio_home)

    @staticmethod
    def get_server(kleio_home: str = None, kleio_version="latest"):
        """Check if a kleio server is running in docker mapped to a given kleio home directory.

        If yes return a KleioServer object, otherwise return None
        If a specific version is required, it can be specified in kleio_version

        Args:
            kleio_home (str, optional): kleio home directory;
                                        defaults to None -> any kleio home.

        Returns:
            KleioServer or None: KleioServer object or None
        """
        if is_docker_running() is False:
            raise Exception("Docker is not running")

        container = get_kserver_container(
            kleio_home=kleio_home, kleio_version=kleio_version
        )
        if container is not None:
            return KleioServer(container)
        else:
            return None

    @staticmethod
    def is_server_running(kleio_home: str = None, kleio_version="latest"):
        """Check if a kleio server is running in docker mapped to a given kleio home directory.

        Args:
            kleio_home (str, optional): kleio home directory;
                                        defaults to None -> any kleio home.
            kleio_version (str, optional): kleio server version; defaults to "latest"
                                            if not specified only checks latest
        Return True of False

        Args:
            kleio_home (str, optional): kleio home directory;
                                        defaults to None -> any kleio home.

        Returns:
            bool: True if server is running, False otherwise
        """
        if is_docker_running() is False:
            raise Exception("Docker is not running")

        container = get_kserver_container(
            kleio_home=kleio_home, kleio_version=kleio_version
        )
        return container is not None

    @staticmethod
    def find_local_kleio_home(path: str = None):
        """Find kleio home directory.

        Kleio home directory is the directory where Kleio Server finds sources and auxiliary
        files like structures, mappings and inferences.

        It can be in the current directory, parent directory, or tests directory.
        It can be named "kleio-home", "timelink-home", or "mhk-home".

        A special case is when the current directory is "notebooks".
        In this case, kleio-home is assumed to be the parent directory of "notebooks"
        and thus set up as the timelink-project template.

        Args:
            path (str, optional): path to start searching from;
                                defaults to None -> current directory.

        Returns:
            str: kleio home directory
        """
        return find_local_kleio_home(path=path)

    @staticmethod
    def make_token():
        """Get the kleio server token from environment or generate a new one if not set.

        Returns:
            str: kleio server token
        """
        token = os.environ.get("KLEIO_ADMIN_TOKEN")
        if token is None:
            token = random_token()
            os.environ["KLEIO_ADMIN_TOKEN"] = token
        return token

    def __init__(
        self,
        container: docker.models.containers.Container = None,
        url: str = None,
        token: str = None,
        kleio_home: str = None,
    ):
        """Not to be used directly.

        See :py:meth:`KleioServer.start` and :meth:`KleioServer.attach`

        To start a kleio server locally in docker use :meth:`KleioServer.start`

        To attach to a running kleio server, local or remote, use :meth:`KleioServer.attach`

        Args:
            container (docker.models.containers.Container): runing kleio server container;
                                        if container is None, then url, token and kleio_home
                                        must be provided.
            url (str): kleio server url if running in a different machine (container=None)
            token (str): kleio server token if running in a different machine (container=None)
            kleio_home (str): kleio server home directory. If None and container is not None
                                    then kleio_home is obtained from the container.
                                    If not none
        """
        if container is None:
            if url is None:
                raise ValueError("url must be provided if container is None")
            if token is None:
                raise ValueError("token must be provided if container is None")
            if kleio_home is None:
                raise ValueError("kleio_home must be provided if container is None")
            self.url = url

            self.kleio_admin_token = token
            self.kleio_home = kleio_home
            self.container = None
            return

        if is_docker_running() is False:
            raise Exception("Docker is not running")

        self.container = container
        port = None
        try:
            p = list(container.attrs["HostConfig"]["PortBindings"])[0]
            port = container.attrs["HostConfig"]["PortBindings"][p][0]["HostPort"]
        except Exception as e:
            error_message = f"Could not get port from container {e}"
            logging.error(error_message)
            raise KleioServerDockerException(error_message)

        self.url = f"http://127.0.0.1:{port}"
        self.kleio_home = [
            mount["Source"]
            for mount in container.attrs["Mounts"]
            if mount["Destination"] == "/kleio-home"
        ][0]
        self.kleio_admin_token = [
            env
            for env in container.attrs["Config"]["Env"]
            if env.startswith("KLEIO_ADMIN_TOKEN")
        ][0].split("=")[1]

    def get_token(self):
        """Get the kleio server token

        Returns:
            str: kleio server token
        """
        return self.kleio_admin_token

    def get_kleio_home(self):
        """Get the kleio server home directory

        Returns:
            str: kleio server home directory
        """
        return self.kleio_home

    def get_container(self):
        """Get the kleio server container

        Returns:
            docker.models.containers.Container: kleio server container
        """
        return self.container

    def get_url(self):
        """Get the kleio server url

        Returns:
            str: kleio server url
        """
        return self.url

    def __str__(self):
        return f"KleioServer(url={self.url}, kleio_home={self.kleio_home})"

    def call(self, method: str, params: dict, token: str = None, timeout=60):
        """Call kleio server API

        Args:
            method (str): kleio server API method
            params (dict): kleio server API method parameters
            token (str, optional): kleio server token; defaults to None -> use admin token
            timeout (int, optional): timeout in seconds; defaults to 60.

        Returns:
            dict: kleio server API response
        """
        url = f"{self.url}/json/"

        if token is None:
            token = self.kleio_admin_token

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        # we add the token to the params
        params["token"] = token
        rpc = request(method, params=params)
        response = requests.post(url, json=rpc, timeout=timeout, headers=headers)
        parsed = parse(response.json())
        if isinstance(parsed, Ok):
            return parsed.result
        elif isinstance(parsed, Error):
            code, message, data, id = parsed
            msg = f"Error {code}: {message} ({data} id:{id})"
            if code == -32006:
                raise KleioServerForbidenException("Forbiden " + msg)
            else:
                raise KleioServer(f"Error {code}: {message} ({data} id:{id})")
        return response

    def stop(self):
        """Stop the kleio server container"""
        self.container.stop()
        self.container.remove()

    def invalidate_user(self, user: str):
        """Invalidate a user

        Args:
            user (str): user to invalidate

        Returns:
            dict: kleio server API response
        """
        pars = {"user": user}
        return self.call("users_invalidate", pars)

    def generate_token(self, user: str, info: TokenInfo):
        """Generate a token for a user

        Args:
            user (str): user to generate token for
            info (TokenInfo): token information

        Returns:
            dict: kleio server API response
        """
        pars = {"user": user, "info": info.model_dump()}
        return self.call("tokens_generate", pars)

    def translation_status(
        self, path: str, recurse: str = "yes", status: str = None, token: str = None
    ) -> List[KleioFile]:
        """Get translations from kleio server

        Args:
            path (str): Path to the directory in sources.
            recurse (str): If "yes", recurse in subdirectories.
            status (str, optional): Filter by translation status. Options include:
                V = valid translations
                T = need translation (source more recent than translation)
                E = translation with errors
                W = translation with warnings
                P = translation being processed
                Q = file queued for translation
            token (str, optional): Kleio server token.

        Returns:
            list[KleioFile]: List of KleioFile objects.

        """
        if recurse is True:
            recurse = "yes"
        elif recurse is False:
            recurse = "no"

        if status is None:
            pars = {"path": path, "recurse": recurse}
        else:
            pars = {"path": path, "recurse": recurse, "status": status}
        translations = self.call("translations_get", pars, token=token)
        result = []
        for t in translations:
            kfile = KleioFile(**t)
            result.append(kfile)
        return result

    def translate(
        self, path: str, recurse: str = "yes", spawn: str = "yes", token=None
    ):
        """Translate sources from kleio server

        :param path: path to the directory in sources
        :type path: str
        :param recurse: if "yes" recurse in subdirectories
        :type recurse: str, optional
        :param spawn: if "yes" spawn a translation process for each file
        :type spawn: str, optional

        :return: kleio server API response
        :rtype: dict
        """
        pars = {"path": path}
        if recurse is True:
            recurse = "yes"
        elif recurse is False:
            recurse = "no"

        if recurse is not None:
            pars["recurse"] = recurse
        if spawn is not None:
            pars["spawn"] = spawn

        return self.call("translations_translate", pars), token

    def translation_clean(self, path: str, recurse: str):
        """clean translations from kleio server

        Removes translation results from kleio server.

        :param path: path to the directory in sources
        :type path: str
        :param recurse: if "yes" recurse in subdirectories
        :type recurse: str

        :return: kleio server API response
        :rtype: dict
        """
        pars = {"path": path, "recurse": recurse}
        return self.call("translations_delete", pars)

    def get_sources(self, path: str, recurse: str, token=None):
        """Get sources from kleio server

        :param path: path to the directory in sources
        :type path: str
        :param recurse: if "yes" recurse in subdirectories
        :type recurse: str

        :return: kleio server API response
        :rtype: dict
        """
        if recurse is True:
            recurse = "yes"
        elif recurse is False:
            recurse = "no"

        pars = {"path": path, "recurse": recurse}
        return self.call("sources_get", pars, token=token)

    def get_report(self, rpt_url: str, token=None) -> str:
        """Get report from kleio server

        :param rpt_url: url of the report in the Kleio Server
        :type rpt_url: str


        :return: kleio server API response
        :rtype: dict
        """

        if not rpt_url.startswith("/"):
            rpt_url = f"/{rpt_url}"

        server_url = f"{self.get_url()}{rpt_url}"
        return self.get_url_content(server_url, token=token)

    def get_url_content(self, server_url: str, token=None, timeout=30) -> str:
        """Get content from Kleio Server

        Args:
            server_url (str): url of the content in the Kleio Server
            token (str, optional): Kleio server token; defaults to None -> use admin token.
            timeout (int, optional): timeout in seconds; defaults to 30.

        """
        if token is None:
            token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        req = urllib.request.Request(server_url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as source:
            response_content = source.read().decode("utf-8")
            return response_content

    def get_home_page(self, token=None) -> str:
        """Get home page from Kleio Server

        Args:
            server_url (str): url of the content in the Kleio Server

        """
        if token is None:
            token = self.get_token
        if token is None:
            headers = {}
        else:
            headers = {"Authorization": f"Bearer {token}"}
        req = urllib.request.Request(self.get_url(), headers=headers)
        with urllib.request.urlopen(req) as source:
            response_content = source.read().decode("utf-8")
            return response_content


def is_docker_running():
    """Check if docker is running"""
    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception as exec:
        logging.error(f"Could not connect to Docker. Is it running? {exec}")
        return False


def find_local_kleio_home(path: str = None):
    """Find kleio home directory.

    Kleio home directory is the directory where Kleio Server finds sources and auxiliary
    files like structures, mappings and inferences.

    It can be in the current directory, parent directory, or tests directory.
    It can be named "kleio-home", "timelink-home", or "mhk-home".

    Special cases:
       * if the current directory is "notebooks", kleio-home is assumed that Kleio home
            to be the parent directory of "notebooks"
       * if there is a "tests" subdirectory, kleio-home is searched in childs of "tests"
    """
    kleio_home = None
    timelink_home_names = ["kleio-home", "timelink-home", "mhk-home"]

    if path is None:
        # get the current directory
        current_dir = os.getcwd()
    else:
        current_dir = path

    # get the user home directory
    user_home = os.path.expanduser("~")

    # check if current_dir is "notebooks"
    if os.path.basename(current_dir) == "notebooks":
        kleio_home = os.path.dirname(current_dir)
    # check if current dir is one of the timelink home names
    elif os.path.basename(current_dir) in timelink_home_names:
        kleio_home = os.path.dirname(current_dir)
    else:
        # check if kleio-home exists in current directory,
        # parents of current directory up to user_home,
        # or tests sub directory of current directory
        dir_path = current_dir
        while dir_path != user_home:
            for home_dir in timelink_home_names:
                if os.path.isdir(f"{dir_path}/{home_dir}"):
                    kleio_home = f"{dir_path}/{home_dir}"
                    break
            if kleio_home:
                break
            dir_path = os.path.dirname(dir_path)
            if dir_path == os.path.dirname(dir_path):
                break  # we reached the root
        if kleio_home is None:
            # check if current_dir is "tests"
            if os.path.isdir(f"{current_dir}/tests"):
                dir_path = f"{current_dir}/tests"
                # check if kleio-home exists in tests directory
                for home_dir in timelink_home_names:
                    if os.path.isdir(f"{dir_path}/{home_dir}"):
                        kleio_home = f"{dir_path}/{home_dir}"
                        break
    if kleio_home is None:
        kleio_home = current_dir
    return kleio_home


def get_kserver_home(
    container: docker.models.containers.Container = None,
    container_number: int = 0,
    kleio_version="latest",
):
    """Get the kleio server home directory

    Args:
        container (docker.models.containers.Container, optional): kleio server container;
                                                         defaults to None -> get by number.
        container_number (int, optional): container number. Defaults to 0.
        kleio_version (str, optional): kleio server version; defaults to "latest"

    Returns the volume mapped to /kleio-home in the kleio server container"""

    if container is None:
        container = get_kserver_container_list(kleio_version=kleio_version)[
            container_number
        ]

    kleio_home = None
    if container is not None:
        kleio_home_mount = [
            mount["Source"]
            for mount in container.attrs["Mounts"]
            if mount["Destination"] == "/kleio-home"
        ]
        if len(kleio_home_mount) > 0:
            kleio_home = kleio_home_mount[0]
        else:
            kleio_home = None
    return kleio_home


def list_kleio_server_containers(
    kleio_version: str = None,
) -> List[Tuple[str, str, int, docker.models.containers.Container]]:
    """List running kleio server containers

    Args:
        kleio_version (str, optional): kleio server version; defaults
                                    to None -> any version.
    Returns:
        a tuple (name, kleio_home, port, token, container) for each container
    """
    containers: list[docker.models.containers.Container] = get_kserver_container_list(
        kleio_version=kleio_version
    )

    if containers is None or len(containers) == 0:
        return []

    result = []
    for container in containers:
        kleio_home = get_kserver_home(container)
        p = list(container.attrs["HostConfig"]["PortBindings"])[0]
        port = container.attrs["HostConfig"]["PortBindings"][p][0]["HostPort"]
        token = get_kserver_token(container)
        result.append((container.name, kleio_home, port, token, container))
    return result


def get_kserver_container(
    kleio_home: str = None, kleio_version="latest", stop_duplicates=False
):
    """Check if a kleio server is running in docker, possibly mapped to
    a given kleio home directory.

    Args:
        kleio_home (str, optional): kleio home directory; defaults to None -> any kleio home.
        kleio_version (str, optional): kleio server version; defaults to "latest"
                                        if not specified only checks latest
        stop_duplicates (bool, optional): if True, stop and remove duplicate containers
                                        with same kleio_home; defaults to False.
    Returns:
        docker.models.containers.Container: the Kleio server container
    """

    containers: list[docker.models.containers.Container] = get_kserver_container_list(
        kleio_version=kleio_version
    )

    if containers is None:
        return None
    elif kleio_home is not None:
        found = False
        kleio_home = os.path.abspath(kleio_home)
        for container in containers:
            kleio_home_mount = [
                mount["Source"]
                for mount in container.attrs["Mounts"]
                if mount["Destination"] == "/kleio-home"
            ]
            if kleio_home_mount[0] == kleio_home:
                if not found:
                    first_found = container
                    found = True
                else:
                    if stop_duplicates:
                        container.stop()
                        container.remove()
                    else:
                        break

        if not found:
            return None
        else:
            return first_found
    else:
        return containers[0]


def get_kserver_container_list(
    kleio_version: str = None,
) -> None | List[docker.models.containers.Container]:
    """Get the Kleio server containers currently running in docker

    Running containers are inspected to detect
    those based on images with "kleio-server" on a tag.

    Args:
        kleio_version (str, optional): kleio server version; defaults to "latest"
    Returns:
        docker.models.containers.Container: the Kleio server container
    """
    if is_docker_running() is False:
        raise Exception("Docker is not running")

    client: docker.DockerClient = docker.from_env()

    allcontainers = client.containers.list()
    allimages_tags = [(t, c) for c in allcontainers for t in c.image.tags]

    if kleio_version is None:
        containers = {c for t, c in allimages_tags if "kleio-server" in t}
    else:
        containers = {
            c for t, c in allimages_tags if f"kleio-server:{kleio_version}" in t
        }

    if len(containers) > 0:
        return list(containers)
    else:
        return None


def get_kserver_token(
    container: docker.models.containers.Container = None,
    container_number: int = 0,
    kleio_version="latest",
) -> str:
    """Get the Kleio server container admin token

    Args:
        container (docker.models.containers.Container, optional): kleio server container;
                                            defaults to None -> get the first container.
        container_number (int, optional): container number. Defaults to 0.
        kleio_version (str, optional): kleio server version; defaults to "latest"

    Returns:
        str: the kleio server container token
    """
    if container is None:
        container = get_kserver_container_list(kleio_version=kleio_version)[
            container_number
        ]

    token = [
        env
        for env in container.attrs["Config"]["Env"]
        if env.startswith("KLEIO_ADMIN_TOKEN")
    ][0].split("=")[1]
    return token


def find_free_port(from_port: int = 8088, to_port: int = 8099):
    for port in range(from_port, to_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                pass
    raise OSError("No free ports available in the range 8088-8099")


def start_kleio_server(
    image: str = "timelinkserver/kleio-server",
    version: str | None = None,
    kleio_home: str | None = None,
    kleio_admin_token: str | None = None,
    kleio_server_port="8088",
    kleio_external_port=None,
    kleio_server_workers="3",
    kleio_idle_timeout=900,
    kleio_conf_dir=None,
    kleio_source_dir=None,
    kleio_stru_dir=None,
    kleio_token_db=None,
    kleio_default_stru=None,
    kleio_debug=None,
    consistency: str = "cached",
    update: bool = False,
    reuse: bool = True,
    stop_duplicates: bool = False,
):
    """Starts a kleio server in docker

    Args:
        image (str, optional): kleio server image. Defaults to "time-link/kleio-server".
        version (str | None, optional): kleio-server version; defaults to "latest".
        kleio_home (str | None, optional): kleio home directory. Defaults to current directory.
        kleio_admin_token (str | None, optional): kleio server token; if None -> generate a random token.
        kleio_server_port (str, optional): kleio server port (in the container). Defaults to "8088".
        kleio_external_port (str, optional): kleio server external port (in the host).
        kleio_server_workers (str, optional): number kleio server workers. Defaults to "3".
        kleio_idle_timeout (int, optional): kleio server idle timeout. Defaults to 900.
        kleio_conf_dir (str, optional): kleio server configuration directory. Defaults to None.
        kleio_source_dir (str, optional): kleio server sources directory. Defaults to None.
        kleio_stru_dir (str, optional): kleio server structures directory. Defaults to None.
        kleio_token_db (str, optional): kleio server token database. Defaults to None.
        kleio_default_stru (str, optional): kleio server default structure. Defaults to None.
        kleio_debug (str, optional): kleio server debug level. Defaults to None.

        consistency (str, optional): consistency of the volume mount. Defaults to "cached".
        port (int, optional): port to map to 8088, if none find a free port starting at 8088.
        update (bool, optional): update kleio server image. Defaults to False.
        reuse (bool, optional): if True, reuse an existing kleio server container
                                    with same keio_home; defaults to True.
        stop_duplicates (bool, optional): if True, stop and remove duplicate containers

    Usage:
        update=True will pull the latest image; if it is newer than existing one
        any container running with the same kleio_home will be stopped and removed,
        a new container will be started with the new image and reuse=True will be ignored.

    """
    # check if kleio server is already running in docker
    if is_docker_running() is False:
        raise RuntimeError("Docker is not running")

    exists = get_kserver_container(
        kleio_home=kleio_home, kleio_version=version, stop_duplicates=stop_duplicates
    )

    client = docker.from_env()
    if update is True:
        if version is None:
            get_version = "latest"
        else:
            get_version = version

        # Pull the latest image
        latest_image = client.images.pull(
            "timelinkserver/kleio-server", tag=get_version
        )

        # Get the currently used image
        current_image = client.images.get(f"timelinkserver/kleio-server:{get_version}")

        # Compare the IDs
        if latest_image.id != current_image.id:
            logging.info("A newer version is available.")
            if exists is not None:
                logging.info("Current container was stopped and removed.")
                exists.stop()
                exists.remove()
                exists = None

        else:
            logging.info("You are using Kleio Server %s (updated)", get_version)

    if exists is not None:
        if reuse:
            return exists
        else:  # if exists and not reuse stop existing
            exists.stop()
            exists.remove()

    # if kleio_home is None, use current directory
    if kleio_home is None:
        kleio_home = os.getcwd()
    else:
        kleio_home = os.path.abspath(kleio_home)
        # check if dir exists
        if not os.path.exists(kleio_home):
            raise FileNotFoundError(f"Directory {kleio_home} does not exist")

    # ensure that kleio_home/system/conf/kleio exists
    # TODO: remove this
    # os.makedirs(f"{kleio_home}/system/conf/kleio", exist_ok=True)

    if kleio_admin_token is None:
        kleio_admin_token = random_token()

    if kleio_external_port is None:
        kleio_external_port = find_free_port(8088, 8099)

    kleio_env = dict()
    if kleio_conf_dir is not None:
        kleio_env["KLEIO_CONF_DIR"] = kleio_conf_dir
    if kleio_source_dir is not None:
        kleio_env["KLEIO_SOURCE_DIR"] = kleio_source_dir
    if kleio_stru_dir is not None:
        kleio_env["KLEIO_STRU_DIR"] = kleio_stru_dir
    if kleio_token_db is not None:
        kleio_env["KLEIO_TOKEN_DB"] = kleio_token_db
    if kleio_default_stru is not None:
        kleio_env["KLEIO_DEFAULT_STRU"] = kleio_default_stru
    if kleio_debug is not None:
        kleio_env["KLEIO_DEBUG"] = kleio_debug
    if kleio_server_workers is not None:
        kleio_env["KLEIO_SERVER_WORKERS"] = kleio_server_workers
    if kleio_idle_timeout is not None:
        kleio_env["KLEIO_IDLE_TIMEOUT"] = kleio_idle_timeout
    if kleio_admin_token is not None:
        kleio_env["KLEIO_ADMIN_TOKEN"] = kleio_admin_token
    if kleio_home is not None:
        kleio_env["KLEIO_HOME"] = kleio_home
    if kleio_server_port is not None:
        kleio_env["KLEIO_SERVER_PORT"] = kleio_server_port

    kleio_container = client.containers.run(
        image=f"{image}:{version}",
        detach=True,
        ports={f"{kleio_server_port}/tcp": kleio_external_port},
        environment=kleio_env,
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

    timeout = 15
    stop_time = 1
    elapsed_time = 0
    # this necessary to get the status
    cont = client.containers.get(kleio_container.id)
    while cont.status not in ["running"] and elapsed_time < timeout:
        sleep(stop_time)
        cont = client.containers.get(kleio_container.id)
        elapsed_time += stop_time
    if cont.status != "running":
        raise RuntimeError("Kleio server did not start")

    return kleio_container


def random_token(length=32):
    """Generate a random token"""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for i in range(length))


def stop_kleio_server(container: docker.models.containers.Container = None):
    """Stop kleio server"""
    if is_docker_running() is False:
        raise Exception("Docker is not running")

    if container is None:
        container = get_kserver_container()

    container = get_kserver_container()
    container.stop()
    container.remove()
