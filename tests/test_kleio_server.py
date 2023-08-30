""" tests for interfacing to kleio server

Teste

https://github.com/time-link/timelink-kleio-server
"""
import timelink.kleio.kleio_server as kleio_server
from tests import skip_on_travis, TEST_DIR

@skip_on_travis
def test_is_kleio_server_running():
    """Test if kleio server is running"""
    assert kleio_server.is_kserver_running() is True or False


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
def test_start_kleio_server():
    """Test if kleio server is started"""
    kleio_server.start_kleio_server()
    assert kleio_server.is_kserver_running() is True