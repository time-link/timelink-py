import os
import warnings
from typing import Dict, List

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, session
from sqlalchemy_utils import database_exists, create_database

from timelink.api import database
from timelink import mhk
from timelink.app.models.user import User, UserProperty, Base
from timelink.app.models.project import ProjectAccess, Project
from timelink.app.schemas.user import UserPropertySchema, UserSchema
from timelink.app.schemas import UserProjectSchema
from timelink.app.services.auth import FiefUserInfo


class UserDatabase:
    def __init__(
        self,
        db_name: str = " timelink_users.sqlite",
        db_type: str = "sqlite",
        db_url=None,
        db_user=None,
        db_pwd=None,
        db_path=None,
        postgres_image=None,
        postgres_version=None,
        initial_users=None,
        stop_duplicates=True,
        **connect_args,
    ):
        """Create a new UserDatabase object.

        Args:
            db_name: the name of the database
            db_type: the type of the database (sqlite, postgres)
            db_url: the url of the database
            db_user: the user to access the database
            db_pwd: the password to access the database
            db_path: the path to the database file
            postgres_image: the docker image of the postgres server
            postgres_version: the version of the postgres server
            stop_duplicates: if True, stop duplicates in the database

        Usage:
            ``python
            db = UserDatabase(db_name='test-users')
            with db.session() as session:
                user = User(name='Test User', fullname='Test User Fullname', email='xpto@xpto.com', nickname='Test Nickname')
                session.add(user)
                session.commit()

            # or manage the session in UserDatabase
            db.start_session()  # returns a session

            db.add_user(user)  # no need to specify the session
            db.commit()   # or db.rollback()
            db.close_session()

            # if you want to use the same session
            session = db.current_session``

        """
        self.db_name = None
        self.db_url = None
        self.db_user = None
        self.db_pwd = None
        self.db_path = None
        self.db_type = db_type
        self.db_container = None
        self.engine = None
        self.session = None
        self.current_session = None
        self.metadata = None
        self.cache: Dict[str, UserSchema] = {}

        if db_name is None:
            raise ValueError("db_name cannot be None")
        self.db_name = db_name

        if self.db_type is None:
            self.db_type = "sqlite"

        # if we received a url, use it to connect
        if db_url is not None:
            self.db_url = db_url
        # if not, generate a url from other parameters
        else:
            if db_type == "sqlite":
                if db_name == ":memory:":
                    self.db_url = "sqlite:///:memory:"
                else:
                    if db_path is None:
                        db_path = os.getcwd()
                        warnings.warn(
                            "No path for the database was specified. Using the current working directory.",
                            stacklevel=2,
                        )
                    if connect_args is None:
                        connect_args = {"check_same_thread": False}
                    db_path = os.path.abspath(db_path)
                    os.makedirs(db_path, exist_ok=True)
                    self.db_url = f"sqlite:///{db_path}/{self.db_name}"
            elif db_type == "postgres":
                if db_pwd is None:
                    self.db_pwd = database.get_db_password()
                else:
                    self.db_pwd = db_pwd
                if db_user is None:
                    self.db_user = "postgres"
                else:
                    self.db_user = db_user
                if database.is_postgres_running():
                    self.db_container = database.get_postgres_container()
                    # if it it is running, we need the password
                    container_vars = self.db_container.attrs["Config"]["Env"]
                    pwd = [var for var in container_vars if "POSTGRES_PASSWORD" in var][
                        0
                    ]
                    self.db_pwd = pwd.split("=")[1]
                    usr = [var for var in container_vars if "POSTGRES_USER" in var][0]
                    self.db_user = usr.split("=")[1]
                else:
                    self.db_container = database.start_postgres_server(
                        self.db_name,
                        self.db_user,
                        self.db_pwd,
                        image=postgres_image,
                        version=postgres_version,
                    )
                self.db_url = (
                    f"postgresql://{self.db_user}:"
                    f"{self.db_pwd}@127.0.0.1/{self.db_name}"
                )
                self.db_container = database.start_postgres_server(
                    self.db_name, self.db_user, self.db_pwd
                )
                self.db_pwd = database.get_postgres_container_pwd()
            elif db_type == "mysql":
                self.db_url = f"mysql://{db_user}:{db_pwd}@localhost/{db_name}"
                if db_pwd is None:
                    try:
                        self.db_pwd = mhk.utilities.get_mhk_db_pwd()
                    except TypeError:
                        self.db_pwd = None
                if db_pwd is None:
                    self.db_pwd = database.random_password()
                # TODO Start a mysql server in docker
            else:
                raise ValueError(f"Unknown database type: {db_type}")

        self.engine = create_engine(self.db_url, connect_args=connect_args)
        if not database_exists(self.engine.url):
            create_database(self.engine.url)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.current_session = None
        self.metadata = Base.metadata
        Base.metadata.create_all(self.engine)
        if initial_users is not None:
            with self.session() as session:
                for user in initial_users:
                    user_exists = self.get_user_by_name(user.name, session=session)
                    if user_exists is None:
                        self.add_user(user, session=session)
                session.commit()

    def __enter__(self):
        self.current_session = self.session()
        return self.current_session

    def __exit__(self, exc_type, exc_value, traceback):
        self.current_session.close()

    def drop_db(self):
        """Drop the database"""
        self.metadata.drop_all(self.engine)

    def commit(self):
        """Commit the current session"""
        self.current_session.commit()

    def rollback(self):
        """Rollback the current session"""
        self.current_session.rollback()

    def add_user(self, user: User, session: session = None):
        """Add a user to the database

        Args:
            user: the user to add

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either: pass a session=session or  "
                    "do db.start_session() before and db.close_session() or "
                    "use context manager with db:"
                )
            else:
                session = self.current_session

        if self.get_user_by_email(user.email, session=session) is not None:
            raise ValueError("An user with that email already exists.")

        session.add(user)

    def on_board_user(self, user: FiefUserInfo, permissions: str = None, session=None):
        """On board an user registered on Fief

        Gets email, name and fields from fief and adds it to the database.

        Adds permissions if provided. Permissions should be fetched
        from the fief access_token and passed as a comma separeted string.

        The access_token is stored in a cookie and can be validated with
        fief.validate_access_token

        """

        user_email = user["email"]
        user_in_db = self.get_user_by_email(user_email, session=session)
        if user_in_db is None:
            user_fields = user.get("fields", {})
            user_name = user_fields.get("user_name", "")
            user_nickname = user_fields.get("user_nickname", None)
            if user_nickname is None:
                user_nickname = user_email.split("@")[0]
            user = User(name=user_name, nickname=user_nickname, email=user_email)
            self.add_user(user, session=session)
            session.commit()
        for field_name, field_value in user["fields"].items():
            self.set_user_property(
                user_in_db.id, field_name, field_value, session=session
            )
        session.commit()
        # todo: think about this
        for permission in permissions:
            self.set_user_property(
                user_in_db.id, f"permission:{permission}", "yes", session=session
            )
        session.commit()

        return UserSchema.model_validate(user_in_db)

    def set_user_property(
        self, user_id: int, property_name: str, property_value: str, session=None
    ):
        """Add a user property to the database

        Args:
            user_id: the id of the user
            property_name: the name of the property
            property_value: the value of the property

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db: , with db as session"
                )
            else:
                session = self.current_session
        # check if property already exists

        user_property = session.scalars(
            select(UserProperty).filter(
                UserProperty.user_id == user_id, UserProperty.name == property_name
            )
        ).first()
        if user_property is not None:
            user_property.value = property_value
            session.merge(user_property)
        else:
            user_property = UserProperty(
                name=property_name, value=property_value, user_id=user_id
            )  # pylint: disable=no-member
            session.add(user_property)

    def get_user(self, user_id: int, session=None) -> User:
        """Get a user from the database

        Args:
            user_id: the id of the user to get

        Returns:
            the user with the given id

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with session=db:"
                )
            else:
                session = self.current_session
        user: User = session.get(User, user_id)
        if user is None:
            return None
        else:
            return user

    def get_user_by_name(self, name: str, session=None) -> User:
        """Get a user from the database

        Args:
            name: the name of the user to get
            session: a database session

        Returns:
            the user with the given name

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with session=db:"
                )
            else:
                session = self.current_session

        user: User = session.scalars(select(User).filter(User.name == name)).first()
        if user is None:
            return None
        else:
            return user

    def get_user_by_email(self, email, session=None):
        """
        Retrieve a user from the database using their email address.

        Args:
            email (str): The email address of the user to retrieve.
            session (Session, optional): The session to use for the query.
                If None, the current session will be used. Defaults to None.

        Returns:
            User: The User object that matches the given email address,
                or None if no user was found.
        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        user: User = session.scalars(select(User).filter(User.email == email)).first()
        if user is None:
            return None
        else:
            return user

    def get_user_by_nickname(self, nickname, session=None):
        """
        Retrieve a user from the database using their nickname.

        Args:
            nickname (str): The nickname address of the user to retrieve.
            session (Session, optional): The session to use for the query.
                If None, the current session will be used. Defaults to None.

        Returns:
            User: The User object that matches the given nickname,
                or None if no user was found.
        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        user: User = session.scalars(
            select(User).filter(User.nickname == nickname)
        ).first()
        if user is None:
            return None
        else:
            return user

    def update_user(self, user: User, session=None):
        """Update a user in the database

        Args:
            user: the user to update

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        session.merge(user)

    def delete_user(self, user: User, session=None):
        """Delete a user from the database

        Args:
            user: the user to delete

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        session.delete(user)
        session.commit()

    def get_user_properties(
        self, user_id: int, session=None
    ) -> List[UserPropertySchema]:
        """Get the properties of a user

        Args:
            user_id: the id of the user

        Returns:
            a list with the properties of the user

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session
        result = session.scalars(
            select(UserProperty).filter(UserProperty.user_id == user_id)
        ).all()
        return result

    def get_user_property(
        self, user_id: int, property_name: str, session=None
    ) -> UserPropertySchema:
        """Get a user property

        Args:
            user_id: the id of the user
            property_name: the name of the property

        Returns:
            the property with the given name

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        r = session.scalars(
            select(UserProperty).filter(
                UserProperty.user_id == user_id, UserProperty.name == property_name
            )
        ).first()
        return r

    def set_user_project_access(
        self, user_id: int, project_id: int, access_level: str, session=None
    ):
        """Set the access level of a user to a project

        Args:
            user_id: the id of the user
            project_id: the id of the project
            access_level: the access level

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        project_access = session.scalars(
            select(ProjectAccess).filter(
                ProjectAccess.user_id == user_id, ProjectAccess.project_id == project_id
            )
        ).first()
        if project_access is not None:
            project_access.access_level = access_level
            session.merge(project_access)
        else:
            project_access = ProjectAccess(
                user_id=user_id, project_id=project_id, access_level=access_level
            )
            session.add(project_access)

    def get_user_project_access(
        self, user_id: int, project_id: int, session=None
    ) -> ProjectAccess:
        """Get the access level of a user to a project

        Args:
            user_id: the id of the user
            project_id: the id of the project

        Returns:
            the access level of the user to the project

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session

        return session.scalars(
            select(ProjectAccess).filter(
                ProjectAccess.user_id == user_id, ProjectAccess.project_id == project_id
            )
        ).first()

    def get_user_projects(self, user_id: int, session=None) -> List[UserProjectSchema]:
        """Get the projects of a user

        Args:
            user_id: the id of the user

        Returns:
            a list with the projects of the user

        """
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with db as session:"
                )
            else:
                session = self.current_session
        stmt = (
            select(
                Project.id,
                Project.name,
                Project.description,
                ProjectAccess.access_level,
            )
            .join(Project.users)
            .filter(ProjectAccess.user_id == user_id)
        )
        result = session.execute(stmt).all()

        projects = []
        for pid, name, description, user_access in result:
            user_project = UserProjectSchema(
                project_id=pid,
                user_id=user_id,
                project_name=name,
                project_description=description,
                access_level=user_access,
            )
            projects.append(user_project)

        return projects

    def get_project(self, project_id: int, session=None) -> Project:
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with session=db:"
                )
            else:
                session = self.current_session

        return session.get(Project, project_id)

    def get_project_by_name(self, name: str, session=None) -> Project:
        if session is None:
            if self.current_session is None:
                raise ValueError(
                    "No session available."
                    "Either pass a session or "
                    "with session=db:"
                )
            else:
                session = self.current_session

        result = session.scalars(select(Project).filter(Project.name == name))
        if result is not None:
            return result.first()
        else:
            return None
