"""Unit test package for timelink."""
# pylint: disable=unused-import, import-error
import os
from pathlib import Path
import random
import time
import warnings

from sqlalchemy.orm import sessionmaker
import pytest

from timelink.kleio.kleio_server import KleioServer
from timelink.kleio.schemas import KleioFile

# See https://docs.sqlalchemy.org/en/14
#      /orm/session_basics.html#when-do-i-make-a-sessionmaker
# Tests should import from here to access the session
#

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
# conn_string local file version
# from pathlib import Path
# sqlite_db = Path(TEST_DIR, "/sqlite/test.db")
# conn_string = f'sqlite://{sqlite_db}?check_same_thread=False'

# con_string sqlite in memory version
conn_string = "sqlite://?check_same_thread=False"

Session = sessionmaker()

mhk_absent = pytest.mark.skipif(
    not Path(Path.home(), ".mhk").is_file(), reason="MHK not present"
)

skip_on_travis = pytest.mark.skipif(
    os.environ.get('TRAVIS') == 'true',
    reason="this test requires file system access for sqlite"
)


def get_one_translation(kserver: KleioServer,
                        path="",
                        max_wait=120) -> KleioFile:
    """Get one translation from the server"""
    translations = kserver.translation_status(path=path, recurse="yes", status="V")
    if len(translations) == 0:
        need_translation = kserver.translation_status(path=path, recurse="yes", status="T")
        if len(need_translation) == 0:
            raise RuntimeError(f"No files available for translation, path={path}")

        one_translation = random.choice(need_translation)
        kserver.translate(path=one_translation.path, recurse="no")

        counter = 0
        wait_for = 1
        max_counter = max_wait / wait_for
        translations = kserver.translation_status(path=path, recurse="yes", status="V")
        in_process = kserver.translation_status(path=path, recurse="yes", status="P")
        while len(translations) == 0 and (counter < max_counter
                                          or len(in_process) > 0):  # noqa: W503
            time.sleep(wait_for)
            counter += 1
            if counter % 20 == 0:
                warnings.warn(f"Waiting for translations {one_translation.name}, counter={counter}",
                              stacklevel=1)
            translations = kserver.translation_status(path=path, recurse="yes", status="V")
            in_process = kserver.translation_status(path=path, recurse="yes", status="P")

    if len(translations) > 0:
        kleio_file: KleioFile = random.choice(translations)
    else:
        raise RuntimeError("No translations available in server")

    return kleio_file
