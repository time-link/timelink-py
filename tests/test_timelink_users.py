import time
from timelink.api import database
from timelink.app.models.user import User, UserProperty  # noqa

import pytest
from sqlalchemy import select
from timelink.app.models.user import Base, User, UserProperty
from timelink.app.models.user_database import UserDatabase
import random
import string

@pytest.fixture(scope='module')
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_path = request.param
    db_user = None
    db_pwd = None
    if db_type == "postgres":
        database.start_postgres_server()
        db_user = database.get_postgres_container_user()
        db_pwd = database.get_postgres_container_pwd()

    dbsystem = UserDatabase(
        db_name=db_name,
        db_type=db_type,
        db_user=db_user,
        db_pwd=db_pwd)

    try:
        yield dbsystem
    finally:
        # dbsystem.drop_db
        dbsystem.session().close()

@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_path
        ("sqlite", ":memory:", None),
        ("postgres", "tests_users", None),
    ],
    indirect=True,
)
def test_create_user_with_properties(dbsystem):

    with dbsystem.session() as session:
        user = User(name='Test User', fullname='Test User Fullname', email='xpto@xpto.com', nickname='Test Nickname')
        session.add(user)
        session.commit()

        random_value1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        random_value2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        property1 = UserProperty(name='property1', value=random_value1, user_id=user.id)
        property2 = UserProperty(name='property2', value=random_value2, user_id=user.id)

        session.add(property1)
        session.add(property2)
        session.commit()

        user = session.scalars(select(User).filter_by(name = 'Test User')).first()

        assert len(user.properties) == 2

        # compare disregarding microseconds
        assert (user.updated.replace(microsecond=0)
                 == user.created.replace(microsecond=0))

        time.sleep(1)

        user.nickname = 'Test Nickname Updated'
        session.commit()

        user = session.scalars(select(User).filter_by(name = 'Test User')).first()
        assert user.updated > user.created

@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_path
        ("sqlite", ":memory:", None),
        ("postgres", "tests_users", None),
    ],
    indirect=True,
)
def test_create_user_db(dbsystem):
    db: UserDatabase = dbsystem
    user = User(name='User2', fullname='Full Name', email='xpto@xpto.com', nickname='Test Nickname')
    db.add_user(user)
    user2 = db.get_user_by_name('User2')
    assert user2 is not None

