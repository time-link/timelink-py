import os
import docker

from sqlalchemy import create_engine, select, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy_utils import database_exists, create_database

from typing import List

from timelink.api import database
from timelink import mhk
from .user import User, UserProperty, Base


class UserDatabase:
    def __init__(
            self,
            db_name: str =' timelink_users',
            db_type: str = 'sqlite',
            db_url=None,
            db_user=None,
            db_pwd=None,
            db_path=None,
            postgres_image=None,
            postgres_version=None,
            stop_duplicates=True,
            **connect_args
    ):
        """ Create a new UserDatabase object.

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

        """
        if db_name is None:
            raise ValueError("db_name cannot be None")
        self.db_name = db_name

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
                    if connect_args is None:
                        connect_args = {"check_same_thread": False}
                    db_path = os.path.abspath(db_path)
                    os.makedirs(db_path, exist_ok=True)
                    self.db_url = f"sqlite:///{db_path}/{self.db_name}.sqlite"
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
        self.metadata = Base.metadata
        Base.metadata.create_all(self.engine)

    def add_user(self, user: User):
        """ Add a user to the database

        Args:
            user: the user to add

        """
        with self.session() as s:
            s.add(user)
            s.commit()

    def set_user_property(self, user_id: int, property_name: str, property_value: str):
        """ Add a user property to the database

        Args:
            user_id: the id of the user
            property_name: the name of the property
            property_value: the value of the property

        """
        # check if property already exists
        with self.session() as s:
            user_property = s.select(UserProperty).filter(UserProperty.user_id == user_id, UserProperty.name == property_name).first()
            if user_property is not None:
                user_property.value = property_value
            else:
                user_property = UserProperty(name=property_name, value=property_value, user_id=user_id) # pylint: disable=no-member
            s.add(user_property)
            s.commit()

    def get_user(self, user_id: int) -> User:
        """ Get a user from the database

        Args:
            user_id: the id of the user to get

        Returns:
            the user with the given id

        """
        with self.session() as s:
            return s.get(User, user_id)

    def get_user_by_name(self, name: str) -> User:
        """ Get a user from the database

        Args:
            name: the name of the user to get

        Returns:
            the user with the given name

        """
        with self.session() as s:
            return s.scalars(select(User).filter(User.name == name)).first()

    def update_user(self, user: User):
        """ Update a user in the database

        Args:
            user: the user to update

        """
        with self.session() as s:
            s.merge(user)
            s.commit()

    def delete_user(self, user: User):
        """ Delete a user from the database

        Args:
            user: the user to delete

        """
        with self.session() as s:
            s.delete(user)
            s.commit()

    def get_user_properties(self, user_id: int) -> List[UserProperty]:
        """ Get the properties of a user

        Args:
            user_id: the id of the user

        Returns:
            a list with the properties of the user

        """
        with self.session() as s:
            return s.select(UserProperty).filter(UserProperty.user_id == user_id).all()
