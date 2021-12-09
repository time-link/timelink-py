"""Unit test package for timelink."""
import os
from sqlalchemy.orm import sessionmaker
import pytest

# See https://docs.sqlalchemy.org/en/14/orm/session_basics.html#when-do-i-make-a-sessionmaker
# Tests should import from here to access the session
#
Session = sessionmaker()

skip_on_travis = pytest.mark.skipif(
    os.environ.get('TRAVIS') == 'true',
    reason="this test required file system access for sqlite"
)
