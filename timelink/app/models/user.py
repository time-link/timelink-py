""" Timelink User model

timelink users are registered users of the application.
Each user can be associated with one or more "projects".

A project is a collection of Kleio sources and a database to store the data.

Access of the user to Kleio sources is done through a Kleio server.
In the Kleio server each user has an acess token that determines the
acess level to the sources directory. So for each project the user
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
import os
from typing import List, Optional
from sqlalchemy import String, create_engine, select
from sqlalchemy.orm import DeclarativeBase

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker  # pylint: disable=import-error
from sqlalchemy_utils import database_exists
from sqlalchemy_utils import create_database
import docker  # pylint: disable=import-error

from timelink.api import database
from timelink import mhk

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

    def __repr__(self):
        return f"UserProperty(id={self.id}, name={self.name}, value={self.value}, user_id={self.user_id})"

    def __str__(self):
        return f"UserProperty(id={self.id}, name={self.name}, value={self.value}, user_id={self.user_id})"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str]
    fullname: Mapped[str] = mapped_column(String(30))
    nickname: Mapped[Optional[str]]
    email: Mapped[str]
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    properties: Mapped[List["UserProperty"]] = relationship("UserProperty", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id}, name={self.name}, fullname={self.fullname}, nickname={self.nickname}, created={self.created}, updated={self.updated})"

    def __str__(self):
        sproperties = ', '.join([str(p) for p in self.properties])
        return f"User(id={self.id}, name={self.name}, fullname={self.fullname}, nickname={self.nickname}, created={self.created}, updated={self.updated}, properties={sproperties})"
