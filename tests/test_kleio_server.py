""" tests for interfacing to kleio server

Teste

https://github.com/time-link/timelink-kleio-server
"""
from enum import Enum
import json
import pytest
import timelink.kleio.kleio_server as kleio_server
from tests import skip_on_travis, TEST_DIR
from jsonrpcclient import request, request_json, parse

KLEIO_ADMIN_TOKEN: str = None
KLEIO_LIMITED_TOKEN: str = None
KLEIO_NORMAL_TOKEN: str = None
class TestMode(Enum):
    LOCAL = "local"
    DOCKER = "docker"

mode = TestMode.LOCAL

@pytest.fixture(scope="module", autouse=True)
def setup():
    if mode == TestMode.LOCAL:
        token='mytoken'
        url='http://localhost:8089/json/'
    else:
        """Setup kleio server for tests"""
        token=kleio_server.get_kserver_token()
        url=kleio_server.kleio_get_url()
    return(token,url)


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

@skip_on_travis
def test_kleio_get_url():
    """Test if kleio server url is available"""
    KLEIO_URL = kleio_server.kleio_get_url()
    assert KLEIO_URL is not None

@skip_on_travis
def test_generate_limited_token(setup):
    token,url=setup
    """Generate a token with limited privileges"""
    user: str = "limited_user"
    info = {
        	"comment": "An user that has no privilegis, used to test authorization errors",
            "api": [
                "nothing"
            ],
            "structures": "sources/structures",
            "sources": "sources/reference_sources"
        }

    try:  # we try to invalidade first
        kleio_server.kleio_invalidate_user(user=user, token=token,url=url)
    except:
        pass

    limited_token = kleio_server.kleio_tokens_generate(user, info, token,url=url)    
    assert limited_token is not None


@skip_on_travis
def test_generate_normal_token(setup):
    """Generate a token for normal user"""
    user: str = "normal_user"
    info = {
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
        }
    
    token, url = setup

    try:
        invalidate = kleio_server.kleio_invalidate_user(user=user, token=token,url=url)
    except:
        pass

    KLEIO_NORMAL_TOKEN = kleio_server.kleio_tokens_generate(user, info, token, url)
    assert KLEIO_NORMAL_TOKEN is not None


@skip_on_travis
def test_translations_get(setup):
    """Test if translations are retrieved"""
    path: str = "sources/reference_sources"
    recurse: str = "yes"
    status: str = None
    
    token,url = setup
    translations = kleio_server.kleio_translations_get(path, recurse, status, 
                                                       token=token,
                                                       url=url)
    assert len(translations) > 0
    for t in translations:
        print(json.dumps(t, indent=4))


@skip_on_travis
def test_sources_get(setup):
    """Test if sources are retrieved"""
    path: str = ""
    recurse: str = "yes"

    token, url = setup
    sources = kleio_server.kleio_sources_get(path, recurse, token=token,url=url)
    assert sources is not None