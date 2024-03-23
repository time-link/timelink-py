""" Timelink User model

timelink users are registered users of the application.

Each user can be associated with one or more "projects".

A project is a collection of Kleio sources and a database to store the data.

Access of the user to Kleio sources is done through a Kleio server.
In the Kleio server each user has an acess token that determines the
access level to the sources directory. So for each project the user
needs to have a valid access token to the Kleio server and its url.

Each project is associated with a database. Timelink is tested with
PostgreSQL and SQLite databases.

When using SQLite, the database is a file in the file system.
When using PostgreSQL, each project is associated with a database
(see https://www.postgresql.org/docs/8.0/managing-databases.html)
and each project is associated with a user and a password to access the database.

users have different access levels to the projects. The access levels are:

1. admin: the user has full access to the project, including the ability to associate
    new users to the project.
2. manager: the user has access to the project, can import data and identify
    entities in the data, can add commentaries, but cannot associate new users
    to the project.
3. colaborator: the user has access to the project, cannot import data, but can
    identify entities in the data and add commentaries.
4. viewer: the user has access to the project, but cannot import data, identify
    people or add commentaries.

"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from timelink.app.schemas.user import UserPropertySchema, UserSchema


# declarative base class
class Base(DeclarativeBase):
    pass


class UserProperty(Base):
    __tablename__ = "user_properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(30))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship("User", back_populates="properties")

    def as_schema(self):
        """Return the pydantic model for this object."""
        return UserPropertySchema.model_validate(self)

    def __repr__(self):
        return f"UserProperty(id={self.id}, name={self.name}, value={self.value}, user_id={self.user_id})"

    def __str__(self):
        return f"UserProperty(id={self.id}, name={self.name}, value={self.value}, user_id={self.user_id})"


class User(Base):
    """
    Attributes:
        id (int): Primary key, autoincrement.
        name (str): Required.
        nickname (str): Optional.
        email (str): Required, unique.
        hashed_password (str): Optional.
        disabled (bool): Optional, default is False.
        created (datetime): Required, default is now.
        updated (datetime): Optional, default is now, updated at now.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(unique=True)
    # deprecated. Authentica with Fief
    hashed_password: Mapped[Optional[str]]
    disabled: Mapped[Optional[bool]] = mapped_column(default=False)
    created: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    properties: Mapped[List["UserProperty"]] = relationship(
        "UserProperty", back_populates="user", cascade="all, delete, delete-orphan"
    )

    projects: Mapped[List["ProjectAccess"]] = relationship(  # type: ignore # noqa F821
        "ProjectAccess", back_populates="user", cascade="all, delete, delete-orphan"
    )

    def as_schema(self):
        """Return the pydantic model for this object."""
        us = UserSchema.model_validate(self)
        us.properties = [p.as_schema() for p in self.properties]
        us.projects = [p.as_schema() for p in self.projects]

    def __repr__(self):
        return (
            f"User("
            f"id={self.id}, "
            f"name={self.name}, "
            f"email={self.email}, "
            f"nickname={self.nickname}, "
            f"created={self.created}, "
            f"updated={self.updated})"
        )

    def __str__(self):
        sproperties = ", ".join([str(p) for p in self.properties])
        return (
            f"User("
            f"id={self.id}, "
            f"name={self.name}, "
            f"email={self.email}, "
            f"fullname={self.fullname}, "
            f"nickname={self.nickname}, "
            f"created={self.created}, "
            f"updated={self.updated}, "
            f"properties={sproperties})"
        )
