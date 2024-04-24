import os
import time
import random
import string

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from timelink.api import database
from timelink.app.models.user import User, UserProperty  # noqa
from timelink.app.models.user_database import UserDatabase
from timelink.app.models.project import Project, ProjectAccess


@pytest.fixture(scope="module")
def dbsystem(request: pytest.FixtureRequest):
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
        db_pwd=db_pwd,
        db_path=db_path,
    )

    with dbsystem.session() as session:
        # delete all users and properties
        session.execute(delete(ProjectAccess))
        session.execute(delete(Project))
        session.execute(delete(UserProperty))
        session.execute(delete(User))
        session.commit()

    try:
        yield dbsystem
    finally:
        dbsystem.drop_db
        dbsystem.session().close()


dbparam = pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_path
        ("sqlite", "test_users.sqlite", "tests/db"),
        # see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        # Not working
        # (pytest.param("postgres", "tests_users", None)),
        ("postgres", "tests_users", None),
    ],
    indirect=True,
)


@dbparam
def test_create_user_with_properties(dbsystem):
    db = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db.session() as session:
        user = User(
            name="User One",
            email="one@xpto.com",
            nickname="One",
        )
        session.add(user)
        session.commit()

        random_value1 = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )
        random_value2 = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=10)
        )

        property1 = UserProperty(name="property1", value=random_value1, user_id=user.id)
        property2 = UserProperty(name="property2", value=random_value2, user_id=user.id)

        session.add(property1)
        session.add(property2)
        session.commit()

        user = session.scalars(select(User).filter_by(email="one@xpto.com")).first()

        assert len(user.properties) == 2

        # compare disregarding microseconds
        assert user.updated.replace(microsecond=0) == user.created.replace(
            microsecond=0
        )

        time.sleep(1)

        user.nickname = "One(1)"
        session.commit()

        user = session.scalars(select(User).filter_by(email="one@xpto.com")).first()
        assert user.updated > user.created


@dbparam
def test_create_user_db(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db:
        user = User(
            name="User 2",
            email="two@xpto.com",
            nickname="NumberTwo",
        )
        db.add_user(user)
        db.commit()
        user2 = db.get_user_by_name("User 2")
        assert user2 is not None


@dbparam
def test_set_user_property(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db:  # noqa
        user = User(
            name="User 3",
            email="san@xpto.org",
            nickname="三",
        )
        db.add_user(user)
        db.commit()  # otherwise user.id is None
        db.set_user_property(user.id, "property1", "value1")
        db.set_user_property(user.id, "property2", "value2")
        db.commit()
        user = db.get_user_by_email("san@xpto.org")
        assert user is not None
        assert len(user.properties) == 2
        props = db.get_user_properties(user.id)
        assert len(props) == 2
        proval = db.get_user_property(user.id, "property1")
        assert proval.value == "value1"
        proval = db.get_user_property(user.id, "property2")
        assert proval.value == "value2"


@dbparam
def test_update_user(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db:
        user = User(
            name="User4",
            email="four@xpto.com",
            nickname="Test Nickname",
        )
        db.add_user(user)
        db.commit()
        user = db.get_user_by_email("four@xpto.com")
        assert user.name == "User4"
        user.name = "Quarto Utilizador"
        db.update_user(user)
        db.commit()
        user = db.get_user_by_email("four@xpto.com")
        assert user.name == "Quarto Utilizador"


@dbparam
def test_duplicate_email(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db.session() as session:
        user = User(
            name="User five",
            email="five@xpto.com",
            nickname="five",
        )
        session.add(user)
        session.commit()

        duplicate_user = User(
            name="User six",
            email="five@xpto.com",
            nickname="six",
        )

        with pytest.raises(
            IntegrityError
        ):  # Replace Exception with a more specific exception
            session.add(duplicate_user)
            session.commit()


@dbparam
def test_user_project_access(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db.session() as session:
        user = db.get_user_by_nickname("PU1", session=session)
        if user is None:
            user = User(
                name="Project User one",
                email="project_user_one@xpto.com",
                nickname="PU1",
                projects=[],
            )
        session.add(user)
        session.commit()

        project = session.query(Project).filter_by(name="Project One").first()
        if project is None:
            project = Project(
                name="Project One",
                description="Project One description",
            )
            session.add(project)
            session.commit()

        access_level = "admin"
        db.set_user_project_access(user.id, project.id, access_level, session=session)
        session.commit()
        user = session.scalars(select(User).filter_by(nickname="PU1")).first()
        project_access_list = [(p.project.name, p.access_level)
                               for p in user.projects
                               if p.project.name == project.name]
        assert len(project_access_list) == 1, "Project access not set"

        pa: ProjectAccess = db.get_user_project_access(user.id, project.id, session=session)
        assert pa.access_level.value == access_level, "Project access level not set"

        projects = db.get_user_projects(user.id, session=session)
        assert len(projects) == 1, "User has no projects"


@dbparam
def test_get_project_name(dbsystem):
    db: UserDatabase = dbsystem
    if db.db_type == "postgres":
        if os.environ.get("TRAVIS") == "true":
            pytest.xfail("No postgres on Travis")
    with db.session() as session:
        result = db.get_project_by_name(name="Project One", session=session)
        if result is None:
            project = Project(
                name="Project One",
                description="Project One description",
            )
            session.add(project)
            session.commit()
        else:
            project = result

        project = db.get_project_by_name(name="Project One", session=session)
        assert project is not None, "Project not found"
