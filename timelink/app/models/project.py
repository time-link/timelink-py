""" Timelink projects

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
import enum
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy import Enum
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from .user import Base, User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(4096))
    databaseURL: Mapped[Optional[str]] = mapped_column(String(256))
    kleioServerURL: Mapped[Optional[str]] = mapped_column(String(256))
    created: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    users: Mapped[List["ProjectAccess"]] = relationship("ProjectAccess", back_populates="project")


class AccessLevel(enum.Enum):
    admin = "admin"
    manager = "manager"
    colaborator = "colaborator"
    viewer = "viewer"


class ProjectAccess(Base):
    __tablename__ = "user_project_access"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    access_level: Mapped[Enum] = mapped_column(Enum(AccessLevel))

    user: Mapped["User"] = relationship("User", back_populates="projects")
    project: Mapped["Project"] = relationship("Project", back_populates="users")

    def __repr__(self):
        def __repr__(self):
            return (
                f"UserProjectAccess("
                f"id={self.id}, "
                f"user_id={self.user_id}, "
                f"project_id={self.project_id}, "
                f"access_level={self.access_level})"
            )
