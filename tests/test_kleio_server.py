""" tests for interfacing to kleio server

https://github.com/time-link/timelink-kleio-server
"""

from enum import Enum
import time
import pytest

from tests import TEST_DIR
import timelink.kleio.kleio_server as kleio_server
from timelink.kleio.schemas import KleioFile, TokenInfo
from timelink.kleio.kleio_server import KleioServer, KleioServerForbidenException
import re

KLEIO_ADMIN_TOKEN: str = None
KLEIO_LIMITED_TOKEN: str = None
KLEIO_NORMAL_TOKEN: str = None

KLEIO_SERVER: KleioServer = None


class KleioServerTestMode(Enum):
    LOCAL = "local"
    DOCKER = "docker"


mode = KleioServerTestMode.DOCKER


@pytest.fixture(scope="function", autouse=True)
def setup():
    """setup kleio server for tests

    To run tests with a local Kleio Server outside docker:
    1) set "mode" abose to KleioServerTestMode.LOCAL
    2)Run the server in Prolog loading serverStart.pl and then:

        setenv('KLEIO_ADMIN_TOKEN','mytoken').
        setup_and_run_server(run_debug_server,[port(8089)]).

    """
    if mode == KleioServerTestMode.LOCAL:
        token = "mytoken"
        url = "http://localhost:8089"
        ks = KleioServer.attach(url, token)
    else:
        """Setup kleio server for tests"""
        khome = f"{TEST_DIR}/timelink-home"
        ks = KleioServer.start(kleio_home=khome, reuse=True, update=False)

    return ks


def test_find_kleio_home() -> str:
    """Test if kleio home is found"""
    kleio_home = KleioServer.find_local_kleio_home()
    assert kleio_home is not None


def test_is_kleio_server_running():
    """Test if kleio server is running"""
    ks = KleioServer.get_server()
    assert ks is not None or ks is None


def test_start_kleio_server():
    """Test if kleio server is started"""
    ks = KleioServer.start(kleio_home=f"{TEST_DIR}/timelink-home", update=False)
    assert ks is not None


def test_attach_kleio_server(setup):
    """Test attach to a running kleio server"""
    kserver: KleioServer = setup
    token = kserver.get_token()
    url = kserver.get_url()
    kleio_home = kserver.get_kleio_home()

    ks = KleioServer.attach(url, token, kleio_home)
    assert ks is not None


def test_get_kleio_server_container(setup):
    kserver: KleioServer = setup
    """Test get the container of the running kleio server"""
    container = kserver.get_container()
    assert container is not None


def test_get_kleio_server_token(setup):
    kserver: KleioServer = setup
    """Test if kleio server token is available"""
    assert kserver.get_token() is not None


def test_kleio_get_url(setup):
    kserver: KleioServer = setup
    """Test if kleio server url is available"""
    KLEIO_URL = kserver.get_url()
    assert KLEIO_URL is not None


def test_make_token():
    """Test if a token is generated"""
    assert KleioServer.make_token() is not None


def test_stop_kleio_server(setup):
    kserver: KleioServer = setup
    kome: str = kserver.get_kleio_home()

    """Test if kleio server is stopped"""

    kserver.stop()
    assert KleioServer.get_server(kome) is None
    kleio_home = f"{TEST_DIR}/timelink-home"
    assert KleioServer.get_server(kleio_home) is None
    kserver.start(kleio_home=kleio_home, update=False)
    # wait for server to start
    import time

    time.sleep(1)
    assert KleioServer.is_server_running(kleio_home=kleio_home) is True


def test_generate_limited_token(setup):
    kserver: KleioServer = setup
    """Generate a token with limited privileges"""
    user: str = "limited_user"
    info: TokenInfo = TokenInfo(
        **{
            "comment": "An user that has no privileges, used to test authorization errors",
            "api": [],
            "structures": "projects/test-project/structures",
            "sources": "projects/test-project/sources",
        }
    )

    try:  # we try to invalidade first
        kserver.invalidate_user(user)
    except Exception:
        pass

    limited_token = kserver.generate_token(user, info)
    assert limited_token is not None

    try:
        kserver.translation_status("", recurse=False, token=limited_token)
        raise AssertionError("This should not happen, user has no privileges")
    except KleioServerForbidenException:
        assert True


def test_generate_normal_token(setup):
    """Generate a token for normal user"""
    user: str = "normal_user"
    info: TokenInfo = TokenInfo(
        **{
            "comment": "An user able to translate, upload and "
            "delete files, and also create and "
            "remove directories, in specific sub-directories in kleio-home",
            "api": [
                "sources",
                "kleioset",
                "files",
                "structures",
                "translations",
                "upload",
                "delete",
                "mkdir",
                "rmdir",
            ],
            "structures": "projects/test-project/structures",
            "sources": "projects/test-project/sources",
        }
    )

    kserver: KleioServer = setup

    try:
        invalidated = kserver.invalidate_user(user)
        if invalidated is None:
            print("User not invalidated")
    except Exception:
        pass

    KLEIO_NORMAL_TOKEN = kserver.generate_token(user, info)
    assert KLEIO_NORMAL_TOKEN is not None


def test_get_kserver_home():
    """Test get the mapped kleio home from running server"""

    kleio_home = kleio_server.get_kserver_home()
    assert kleio_home is not None


def test_translations_get(setup):
    """Test if translations are retrieved"""
    path: str = "projects/test-project/kleio/reference_sources/linked_data"
    recurse: str = "yes"
    status: str = None

    kserver: KleioServer = setup
    translations = kserver.translation_status(path,
                                              recurse=recurse,
                                              status=status)
    assert len(translations) > 0

    kfile: KleioFile
    print()
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )
    print()


def test_translations_translate(setup):
    """Test if translations are translated"""
    path: str = "projects/test-project/kleio/reference_sources/linked_data"
    recurse: str = "yes"
    spawn: str = "no"

    kserver: KleioServer = setup
    translations = kserver.translate(path, recurse, spawn)
    assert translations is not None


def test_translations_processing(setup):
    """Test translations in process"""
    path: str = "projects/test_project/"
    recurse: str = "yes"
    status: str = "P"

    kserver: KleioServer = setup
    translations = kserver.translation_status(path, recurse, status)
    assert len(translations) is not None

    kfile: KleioFile
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )


def test_translations_queued(setup):
    """Test translation queued"""
    path: str = "projects/test-project/"
    recurse: str = "yes"
    status: str = "Q"

    kserver: KleioServer = setup
    translations = kserver.translation_status(path, recurse, status)
    assert translations is not None

    kfile: KleioFile
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )


def test_translations_clean(setup):
    """Test if translations results are deleted"""
    path: str = "projects/test-project/kleio/reference_sources/linked_data"
    recurse: str = "yes"

    kserver: KleioServer = setup

    queued = kserver.translation_status(path, recurse, "Q")
    while len(queued) > 0:
        print(f"Waiting for {len(queued)} queued translations to finish")
        import time

        time.sleep(1)
        queued = kserver.translation_status(path, recurse, "Q")

    processing = kserver.translation_status(path, recurse, "P")
    while len(processing) > 0:
        print(f"Waiting for {len(processing)} processing translations to finish")
        import time

        time.sleep(1)
        processing = kserver.translation_status(path, recurse, "P")

    translations = kserver.translation_clean(path, recurse)
    assert translations is not None


def test_sources_get(setup):
    """Test if sources are retrieved"""
    path: str = ""
    recurse: str = "yes"

    kserver: KleioServer = setup
    sources = kserver.get_sources(path, recurse)
    assert sources is not None


def test_homepage_get(setup):
    """Test if homepage is retrieved"""
    url = "https://timelink.uc.pt/kleio"
    ks = KleioServer.attach(url, '', '')
    home = ks.get_home_page()
    # extract lines with pattern "([A-Za-z_]+):(.*)"
    pattern = re.compile(r"([A-Za-z_\ ]*):(.*)")

    matches = pattern.findall(home)
    home_page_info = {}
    for key, value in matches:
        print(f"{key} = {value}")
        home_page_info[key] = value
    version = home_page_info['Version']
    assert version is not None


def test_start_kleio_server_env():
    """Test if kleio server is started with env variables"""
    khome = f"{TEST_DIR}/timelink-home"
    kadmin_token = "0123456789"
    kserver_port = 8089
    kserver_exposed_port = 8989
    kworkers = 5
    kleio_conf_dir = "/kleio-home/systems/conf/kleio"
    kleio_source_dir = "/kleio-home/projects/test-project/sources"
    kleio_structure_dir = "/kleio-home/projects/test-project/structures"
    kleio_default_stru = "/kleio-home/projects/test-project/structures/sources.str"
    kleio_token_db = "/kleio-home/systems/conf/kleio/tokens.db"
    kleio_debug = "true"

    ks = KleioServer.start(
        kleio_home=khome,
        kleio_admin_token=kadmin_token,
        kleio_server_port=kserver_port,
        kleio_external_port=kserver_exposed_port,
        kleio_server_workers=kworkers,
        kleio_idle_timeout=60,
        kleio_conf_dir=kleio_conf_dir,
        kleio_source_dir=kleio_source_dir,
        kleio_stru_dir=kleio_structure_dir,
        kleio_default_stru=kleio_default_stru,
        kleio_token_db=kleio_token_db,
        kleio_debug=kleio_debug,
        reuse=False,
        update=False)

    time.sleep(3)
    home = ks.get_home_page()
    # extract lines with pattern "([A-Za-z_]+):(.*)"
    pattern = re.compile(r"([A-Za-z_\ ]*):(.*)")

    matches = pattern.findall(home)
    home_page_info = {}
    for key, value in matches:
        print(f"{key} = {value}")
        home_page_info[key] = value
    assert home_page_info['Workers'].strip() == str(kworkers), "number of works do not match"
    ptoken = home_page_info['Kleio_admin_token'].strip()
    assert ptoken == kadmin_token[:5], "token does not match"
