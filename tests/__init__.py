"""Unit test package for timelink."""
import os
from pathlib import Path

from sqlalchemy.orm import sessionmaker
import pytest

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
