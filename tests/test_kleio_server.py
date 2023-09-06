""" tests for interfacing to kleio server

Teste

https://github.com/time-link/timelink-kleio-server
"""
import requests
import timelink.kleio.kleio_server as kleio_server
from tests import skip_on_travis, TEST_DIR
from jsonrpcclient import request, request_json, parse

KLEIO_ADMIN_TOKEN: str = None
KLEIO_LIMITED_TOKEN: str = None
KLEIO_NORMAL_TOKEN: str = None

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

@skip_on_travis
def test_generate_limited_token():
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
    token = kleio_server.get_kserver_token()
    invalidate = kleio_server.kleio_invalidate_user(user, token)
    assert invalidate.status_code == 200
    response: requests.Response = kleio_server.kleio_tokens_generate(user, info, token)    
    assert response.status_code == 200

@skip_on_travis
def test_generate_normal_token():
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
    
    token = kleio_server.get_kserver_token()
    invalidate = kleio_server.kleio_invalidate_user(user, token)
    assert invalidate.status_code == 200

    global KLEIO_NORMAL_TOKEN
    KLEIO_NORMAL_TOKEN = kleio_server.kleio_tokens_generate(user, info, token)
    assert KLEIO_NORMAL_TOKEN is not None


@skip_on_travis
def test_translations_get():
    """Test if translations are retrieved"""
    path: str = "sources/reference_sources"
    recurse: str = "yes"
    status: str = None
    
    global KLEIO_NORMAL_TOKEN
    if KLEIO_NORMAL_TOKEN is None:

        KLEIO_NORMAL_TOKEN = kleio_server.get_kserver_token()
    translations = kleio_server.kleio_translations_get(path, recurse, status, KLEIO_NORMAL_TOKEN)
    assert len(translations) > 0

@skip_on_travis
def test_sources_get():
    """Test if sources are retrieved"""
    path: str = ""
    recurse: str = "yes"

    global KLEIO_NORMAL_TOKEN
    if KLEIO_NORMAL_TOKEN is None:
        KLEIO_NORMAL_TOKEN = kleio_server.get_kserver_token()

    sources = kleio_server.kleio_sources_get(path, recurse, KLEIO_NORMAL_TOKEN)
    assert sources is not None