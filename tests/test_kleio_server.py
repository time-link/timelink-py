""" tests for interfacing to kleio server

https://github.com/time-link/timelink-kleio-server
"""
from enum import Enum
import pytest
from jsonrpcclient import request, request_json, parse

from tests import skip_on_travis, TEST_DIR
import os
import timelink.kleio.kleio_server as kleio_server
from timelink.kleio.schemas import KleioFile, TokenInfo
from timelink.kleio.kleio_server import KleioServer

KLEIO_ADMIN_TOKEN: str = None
KLEIO_LIMITED_TOKEN: str = None
KLEIO_NORMAL_TOKEN: str = None

KLEIO_SERVER: KleioServer = None
class TestMode(Enum):
    LOCAL = "local"
    DOCKER = "docker"

mode = TestMode.DOCKER

@pytest.fixture(scope="function", autouse=True)
def setup():
    if mode == TestMode.LOCAL:
        token='mytoken'
        url='http://localhost:8089'
    else:
        """Setup kleio server for tests"""
        if not kleio_server.is_kserver_running():
            kleio_server.start_kleio_server(kleio_home=f"{TEST_DIR}/timelink-home")
        token=kleio_server.get_kserver_token()
        url=kleio_server.kleio_get_url()
    return KleioServer(url=url, token=token)


def test_find_kleio_home() -> str:
    """Test if kleio home is found"""
    kleio_home = kleio_server.find_kleio_home()

    assert kleio_home is not None


@skip_on_travis
def test_is_kleio_server_running():
    """Test if kleio server is running"""
    running = kleio_server.is_kserver_running()
    assert  running == True or running == False

@skip_on_travis
def test_start_kleio_server():
    """Test if kleio server is started"""
    kleio_server.start_kleio_server(kleio_home=f"{TEST_DIR}/timelink-home")
    assert kleio_server.is_kserver_running() is True

@skip_on_travis
def test_get_kleio_server_container():
    """Test if kleio server container is running"""
    assert kleio_server.get_kserver_container() is not None

@skip_on_travis
def test_get_kleio_server_token():
    """Test if kleio server token is available"""
    assert kleio_server.get_kserver_token() is not None

def test_gen_token():
    """Test if a token is generated"""
    assert kleio_server.gen_token() is not None

@skip_on_travis
def test_get_kleio_server_token():
    """Test if kleio server token is available"""
    assert kleio_server.get_kserver_token() is not None
    
@skip_on_travis
def test_stop_kleio_server():
    """Test if kleio server is stopped"""

    kleio_server.stop_kleio_server()
    assert kleio_server.is_kserver_running() is False
    kleio_server.start_kleio_server(kleio_home=f"{TEST_DIR}/timelink-home")
    assert kleio_server.is_kserver_running() is True
    # wait for server to start
    import time
    time.sleep(5)

@skip_on_travis
def test_kleio_get_url():
    """Test if kleio server url is available"""
    KLEIO_URL = kleio_server.kleio_get_url()
    assert KLEIO_URL is not None

@skip_on_travis
def test_generate_limited_token(setup):
    kserver: KleioServer = setup
    """Generate a token with limited privileges"""
    user: str = "limited_user"
    info: TokenInfo = TokenInfo(**{
        	"comment": "An user that has no privileges, used to test authorization errors",
            "api": [
         
            ],
            "structures": "sources/structures",
            "sources": "sources/reference_sources"
        })

    try:  # we try to invalidade first
        kserver.invalidate_user(user)
    except:
        pass

    limited_token = kserver.generate_token(user, info)    
    assert limited_token is not None


@skip_on_travis
def test_generate_normal_token(setup):
    """Generate a token for normal user"""
    user: str = "normal_user"
    info:TokenInfo = TokenInfo(**{
        	"comment": "An user able to translate, upload and delete files, and also create and remove directories, in specific sub-directoris in kleio-home",
            "api": [
                "sources",
                "kleioset",
                "files",
                "structures",
                "translations",
                "upload",
                "delete",
                "mkdir",
                "rmdir"
            ],
            "structures": "structures/reference_sources",
            "sources": "sources/reference_sources"
        })
    
    kserver:KleioServer = setup

    try:
        invalidated = kserver.invalidate_user(user)
    except:
        pass

    KLEIO_NORMAL_TOKEN = kserver.generate_token(user, info)
    assert KLEIO_NORMAL_TOKEN is not None


@skip_on_travis
def test_translations_get(setup):
    """Test if translations are retrieved"""
    path: str = "sources/reference_sources/"
    recurse: str = "yes"
    status: str = None
    
    kserver:KleioServer = setup
    translations = kserver.translation_status(path, recurse, status)
    assert len(translations) > 0

    kfile: KleioFile
    for kfile in translations:
        print(f"{kfile.status} {kfile.path} M:{kfile.modified} T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}")


@skip_on_travis
def test_translations_translate(setup):
    """Test if translations are translated"""
    path: str = "sources/reference_sources/varia/dehergne-a.cli"
    recurse: str = "yes"
    spawn: str = "no"

    kserver: KleioServer = setup
    translations = kserver.translate(path, recurse, spawn)
    assert translations is not None


@skip_on_travis
def test_sources_get(setup):
    """Test if sources are retrieved"""
    path: str = ""
    recurse: str = "yes"

    kserver: KleioServer = setup
    sources = kserver.get_sources(path, recurse)
    assert sources is not None