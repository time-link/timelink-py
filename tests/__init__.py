"""Unit test package for timelink."""

# pylint: disable=unused-import, import-error
import os
import random
import time
import warnings
from enum import Enum
from pathlib import Path

import pytest
import requests

# this is used in some MHK tests
from sqlalchemy.orm import sessionmaker

from timelink.kleio.kleio_server import KleioServer
from timelink.kleio.schemas import KleioFile

# See https://docs.sqlalchemy.org/en/14
#      /orm/session_basics.html#when-do-i-make-a-sessionmaker
# Tests should import from here to access the session
#

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
KLEIO_HOME = Path(TEST_DIR, "timelink-home")

# this will be used in some MHK tests should be deprecated
Session = sessionmaker()

# conn_string local file version
sqlite_db = Path(TEST_DIR, "sqlite/tests.sqlite")

# Extract the directory path
directory = os.path.dirname(sqlite_db)

# Create the directory if it doesn't exist
if not os.path.exists(directory):
    os.makedirs(directory)

conn_string = f"sqlite:///{sqlite_db}?check_same_thread=False"

# con_string sqlite in memory version
# conn_string = "sqlite://?check_same_thread=False"

# path to reference sqlite database
# this is used to test migrations
reference_db = Path(TEST_DIR, "db/reference_db/timelink.sqlite")
reference_db_con_str = f"sqlite:///{reference_db}"

# was: not Path(Path.home(), ".mhk").is_file(), reason="MHK not present")
mhk_absent = pytest.mark.skipif(True, reason="Deprecated tests")

skip_on_travis = pytest.mark.skipif(
    os.environ.get("TRAVIS") == "true",
    reason="this test requires file system access for sqlite",
)

skip_on_github_actions = pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true", reason="this test requires file system access for sqlite"
)

# Backward compatibility - skip on either CI
skip_on_ci = pytest.mark.skipif(
    os.environ.get("TRAVIS") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="this test requires file system access for sqlite"
)


# fixture to skip test if no internet
# Usage:
# @pytest.mark.skipif(not has_internet(), reason="No internet connection available")
def has_internet():
    """Check if there is an internet connection by trying to reach GitHub's domain."""
    try:
        # Attempt to reach GitHub's server. Replace 'https://github.com' with another URL if needed.
        response = requests.head("https://github.com", timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        # If a connection error occurs, there is no internet connection.
        return False


class KleioServerTestMode(Enum):
    LOCAL = "local"
    DOCKER = "docker"


kleio_server_mode = KleioServerTestMode.DOCKER

# determine the image of kleio-server to use.
# "kleio-server" is a local image, can be built in timelink-kleio project
#   with "make build-local". Use for debugging kleio-server fixes
#
# "timelinkserver/kleio-server" is the version in Docker Hub
#     use when testing timelink-py against last public kleio-server images
#
use_kleio_image = "timelinkserver/kleio-server"
# use latest or specific build e.g. 12.8.586
use_kleio_version = "latest"

skip_if_local = pytest.mark.skipif(
    kleio_server_mode == KleioServerTestMode.LOCAL, reason="Skipping test in LOCAL mode"
)


def get_one_translation(kserver: KleioServer, path="", max_wait=120) -> KleioFile:
    """Get one translation from the server"""
    translations = kserver.get_translations(path=path, recurse="yes", status="V")
    if len(translations) == 0:
        need_translation = kserver.get_translations(
            path=path, recurse="yes", status="T"
        )
        if len(need_translation) == 0:
            raise RuntimeError(f"No files available for translation, path={path}")

        one_translation = random.choice(need_translation)
        kserver.translate(path=one_translation.path, recurse="no")

        counter = 0
        wait_for = 1
        max_counter = max_wait / wait_for
        translations = kserver.get_translations(path=path, recurse="yes", status="V")
        in_process = kserver.get_translations(path=path, recurse="yes", status="P")
        while len(translations) == 0 and (
            counter < max_counter or len(in_process) > 0
        ):  # noqa: W503
            time.sleep(wait_for)
            counter += 1
            if counter % 20 == 0:
                warnings.warn(
                    f"Waiting for translations {one_translation.name}, counter={counter}",
                    stacklevel=1,
                )
            translations = kserver.get_translations(
                path=path, recurse="yes", status="V"
            )
            in_process = kserver.get_translations(path=path, recurse="yes", status="P")

    if len(translations) > 0:
        kleio_file: KleioFile = random.choice(translations)
    else:
        raise RuntimeError("No translations available in server")

    return kleio_file
