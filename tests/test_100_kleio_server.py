"""tests for interfacing to kleio server

https://github.com/time-link/timelink-kleio-server
"""

import re
import time
from pathlib import Path

#  import pdb
from tests import TEST_DIR, skip_if_local
from timelink.kleio.kleio_server import (
    KleioServer,
    KleioServerForbidenException,
    is_project_directory,
    is_timelink_home_directory,
)
from timelink.kleio.schemas import KleioFile, TokenInfo

KLEIO_ADMIN_TOKEN: str | None = None
KLEIO_LIMITED_TOKEN: str | None = None
KLEIO_NORMAL_TOKEN: str | None = None
KLEIO_SERVER: KleioServer | None = None


def test_find_kleio_home_project():
    # Test if kleio home is detected in a project dir"""
    project_path = Path(TEST_DIR, "timelink-home", "projects", "test-project")
    kleio_home = KleioServer.find_local_kleio_home(str(project_path))

    assert kleio_home == str(project_path)
    assert is_project_directory(str(project_path))


def test_find_timelink_home():
    # Test if kleio home is detected in a timelink home dir"""
    timelink_home = Path(TEST_DIR, "timelink-home")
    kleio_home = KleioServer.find_local_kleio_home(str(timelink_home))

    assert kleio_home == str(timelink_home)
    assert is_timelink_home_directory(str(timelink_home))


def test_is_kleio_server_running(kleio_server):
    # Test if kleio server is running"""
    kleio_server.get_url()
    ks = KleioServer.get_server()
    assert ks is not None or ks is None


def test_attach_kleio_server(kleio_server):
    # Test attach to a running kleio server"""
    kserver: KleioServer = kleio_server
    token = kserver.get_token()
    url = kserver.get_url()
    kleio_home = kserver.get_kleio_home()

    ks = KleioServer.attach(url, token, kleio_home)
    assert ks is not None


@skip_if_local
def test_get_kleio_server_container(kleio_server):
    kserver: KleioServer = kleio_server
    # Test get the container of the running kleio server"""
    container = kserver.get_container()
    assert container is not None


def test_get_kleio_server_token(kleio_server):
    kserver: KleioServer = kleio_server
    # Test if kleio server token is available"""
    assert kserver.get_token() is not None


def test_kleio_get_url(kleio_server):
    kserver: KleioServer = kleio_server
    # Test if kleio server url is available"""
    KLEIO_URL = kserver.get_url()
    assert KLEIO_URL is not None


def test_make_token():
    # Test if a token is generated"""
    assert KleioServer.make_token() is not None


def test_generate_limited_token(kleio_server):
    kserver: KleioServer = kleio_server
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
        kserver.get_translations("", recurse=False, token=limited_token)
        raise AssertionError("This should not happen, user has no privileges")
    except KleioServerForbidenException:
        assert True


def test_generate_normal_token(kleio_server):
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

    kserver: KleioServer = kleio_server

    try:
        invalidated = kserver.invalidate_user(user)
        if invalidated is None:
            print("User not invalidated")
    except Exception as exception:
        print(exception)
        pass

    KLEIO_NORMAL_TOKEN = kserver.generate_token(user, info)
    assert KLEIO_NORMAL_TOKEN is not None


def test_get_kserver_home(kleio_server):
    # Test get the mapped kleio home from running server"""
    kserver = kleio_server
    kleio_home = kserver.get_kleio_home()
    assert kleio_home is not None


def test_translations_get(kleio_server):
    # Test if translations are retrieved"""
    path: str = "projects/test-project/sources/reference_sources/linked_data"
    recurse: str = "yes"
    status: str | None = None

    kserver: KleioServer = kleio_server
    translations = kserver.get_translations(path, recurse=recurse, status=status)
    assert len(translations) > 0

    kfile: KleioFile
    print()
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )
    print()


def test_translations_translate(kleio_server):
    # Test if translations are translated"""
    path: str = "projects/test-project/sources/reference_sources/linked_data"
    recurse: str = "yes"
    spawn: str = "no"

    kserver: KleioServer = kleio_server
    translations = kserver.translate(path, recurse, spawn)
    assert translations is not None


def test_translations_processing(kleio_server):
    # Test translations in process"""
    path: str = "projects/test_project/"
    recurse: str = "yes"
    status: str = "P"

    kserver: KleioServer = kleio_server
    translations = kserver.get_translations(path, recurse, status)
    assert len(translations) is not None

    kfile: KleioFile
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )


def test_translations_queued(kleio_server):
    # Test translation queued"""
    path: str = "projects/test-project/"
    recurse: str = "yes"
    status: str = "Q"

    kserver: KleioServer = kleio_server
    translations = kserver.get_translations(path, recurse, status)
    assert translations is not None

    kfile: KleioFile
    for kfile in translations:
        print(
            f"{kfile.status} {kfile.path} M:{kfile.modified} "
            f"T:{kfile.translated} E:{kfile.errors} W:{kfile.warnings}"
        )


def test_translations_clean(kleio_server):
    # Test if translations results are deleted"""
    path: str = "projects/test-project/sources/reference_sources/linked_data"
    recurse: str = "yes"

    kserver: KleioServer = kleio_server

    queued = kserver.get_translations(path, recurse, "Q")
    start_time = time.time()
    while len(queued) > 0:
        if time.time() - start_time > 20:
            raise TimeoutError("Queued translations did not finish within 20 seconds")
        print(f"Waiting for {len(queued)} queued translations to finish")

        time.sleep(5)
        queued = kserver.get_translations(path, recurse, "Q")

    processing = kserver.get_translations(path, recurse, "P")
    start_time = time.time()
    while len(processing) > 0:
        if time.time() - start_time > 20:
            raise TimeoutError(
                "Processing translations did not finish within 20 seconds"
            )
        print(f"Waiting for {len(processing)} processing translations to finish")
        time.sleep(5)
        processing = kserver.get_translations(path, recurse, "P")

    translations = kserver.translation_clean(path, recurse)
    assert translations is not None


def test_sources_get(kleio_server):
    # Test if sources are retrieved"""
    path: str = ""
    recurse: str = "yes"

    kserver: KleioServer = kleio_server
    sources = kserver.get_sources(path, recurse)
    assert sources is not None


@skip_if_local
def tests_get_logs(kleio_server):
    # Test if logs are retrieved"""
    kserver: KleioServer = kleio_server
    logs = kserver.get_logs(tail=10)
    print(logs)
    assert logs is not None


def test_homepage_get(kleio_server):
    # Test if homepage is retrieved"""
    url = kleio_server.get_url()
    ks = KleioServer.attach(url, "", "")
    home = ks.get_home_page()
    # extract lines with pattern "([A-Za-z_]+):(.*)"
    pattern = re.compile(r"([A-Za-z_\ ]*):(.*)")

    matches = pattern.findall(home)
    home_page_info = {}
    for key, value in matches:
        print(f"{key} = {value}")
        home_page_info[key] = value
    version = home_page_info["Version"]
    assert version is not None


def test_get_version(kleio_server):
    # Test if homepage is retrieved"""
    url = kleio_server.get_url()
    ks = KleioServer.attach(url, "", "")
    version_info = ks.get_version_info()
    print(version_info)
    assert version_info is not None


@skip_if_local
def test_start_kleio_server_env():
    # Test if kleio server is started with env variables"""
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
        update=False,
    )

    time.sleep(3)
    home = ks.get_home_page()
    # extract lines with pattern "([A-Za-z_]+):(.*)"
    pattern = re.compile(r"([A-Za-z_\ ]*):(.*)")

    matches = pattern.findall(home)
    home_page_info = {}
    for key, value in matches:
        print(f"{key} = {value}")
        home_page_info[key] = value
    assert home_page_info["Workers"].strip() == str(
        kworkers
    ), "number of works do not match"
    ptoken = home_page_info["Kleio_admin_token"].strip()
    assert ptoken == kadmin_token[:5], "token does not match"
    ks.stop()


@skip_if_local
def test_start_stop_kleio_server():
    # pdb.set_trace()
    # kserver: KleioServer = KleioServer.start(kleio_home=KLEIO_HOME, kleio_external_port=8999, reuse=False)
    # kome: str = kserver.get_kleio_home()
    # Test if kleio server is stopped"""
    # kserver.stop()
    # running_server = KleioServer.get_server(kome)
    # assert running_server is None
    pass
