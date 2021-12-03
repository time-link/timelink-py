"""Unit test package for timelink."""
from sqlalchemy.orm import sessionmaker

# See https://docs.sqlalchemy.org/en/14/orm/session_basics.html#when-do-i-make-a-sessionmaker
# Tests should import from here to access the session
#
Session = sessionmaker()
