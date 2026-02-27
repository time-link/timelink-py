import pytest

from tests import KLEIO_HOME, KleioServerTestMode, kleio_server_mode
from timelink.kleio.kleio_server import KleioServer


@pytest.fixture(scope="session")
def kleio_server():
    """setup kleio server for tests

    The kleio_server local mode does not start a new Kleio Server in docker.
    Instead it will attach to a running kleio server at a specific
    url with a specific token (setup above). This is usefull to
    have the server running in swil prolog and debug interactively.

    To run tests with a local Kleio Server outside docker:
    1) set "mode" in __init__.py to KleioServerTestMode.LOCAL
    2)Run the server in Prolog loading serverStart.pl and then:

        setenv('KLEIO_ADMIN_TOKEN','mytoken').
        % PATH_TO_KLEIO_HOME_TEST_PROJECT e.g.:
        % /Users/jrc/develop/timelink-py-worktree/main/tests/timelink-home/
        setenv('KLEIO_HOME_DIR', 'PATH_TO_KLEIO_HOME_TEST_PROJECT').

        setup_and_run_server(run_debug_server,[port(8089)]).

    Or run run_test_server in serverStart.pl and use
    token=mytoken and port 8088. Make sure the port
    is not in use by docker.

    Then use tpsy(predicate) in the Prolog console to debug
    requests comming from the tests in this suite.

    """
    if kleio_server_mode == KleioServerTestMode.LOCAL:
        local = True
    else:
        local = False

    kleio_image = "timelinkserver/kleio-server"
    kleio_version = "latest"
    # For testing a pre release local version of Kleio server
    # kleio_version = "12.9.591"
    # kleio_image = "kleio-server"
    kleio_external_port = 8089
    timeout_secs = 300

    if local:
        token = "mytoken"
        url = "http://localhost:8089"
        server = KleioServer.attach(url, token)
        print("Kleio server attached", server.get_url())
        print("Kleio server version", server.get_version_info())
    else:
        server = KleioServer.start(
            kleio_home=KLEIO_HOME,
            kleio_image=kleio_image,
            kleio_version=kleio_version,
            kleio_external_port=kleio_external_port,
            kleio_debug="true",
        )
        print("Kleio server started in Docker", server.container.name)
        print("Kleio server version", server.get_version_info())
    server.set_call_timeout(timeout_secs)

    yield server

    if not local:
        try:
            print("Stopping kleio server", server.container.name)
            server.stop()
        except Exception as e:
            print("Error stopping server", e)
            pass
