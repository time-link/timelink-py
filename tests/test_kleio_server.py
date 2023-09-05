""" tests for interfacing to kleio server

Teste

https://github.com/time-link/timelink-kleio-server
"""
import requests
import timelink.kleio.kleio_server as kleio_server
from tests import skip_on_travis, TEST_DIR

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
            "sources": "sources/test_translations"
        }
    token = kleio_server.get_kserver_token()
    response: requests.Response = kleio_server.kleio_tokens_generate(user, info, token)    
    
    assert response.status_code == 200