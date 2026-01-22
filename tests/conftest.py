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
    1) set "mode" above to KleioServerTestMode.LOCAL
    2)Run the server in Prolog loading serverStart.pl and then:

        setenv('KLEIO_ADMIN_TOKEN','mytoken').
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

    if local:
        token = "mytoken"
        url = "http://localhost:8088"
        server = KleioServer.attach(url, token)
    else:
        server = KleioServer.start(
            kleio_home=KLEIO_HOME,
            kleio_version="latest",
            kleio_external_port=8080,
            kleio_debug="true",
        )

    yield server

    if not local:
        try:
            print("Stopping kleio server", server.container.name)
            server.stop()
        except Exception as e:
            print("Error stopping server", e)
            pass
