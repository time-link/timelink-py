from datetime import datetime
from typing import List, Optional
import enum
from sqlalchemy import String
from timelink.web.models.user import UserBase, User

from sqlalchemy.orm import Mapped
from sqlalchemy import Enum
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


class Project(UserBase):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, unique=True)
    name: Mapped[str] = mapped_column(String(30), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(4096))
    databaseURL: Mapped[Optional[str]] = mapped_column(String(256))
    kleioServerURL: Mapped[Optional[str]] = mapped_column(String(256))
    solr_core_name: Mapped[Optional[str]] = mapped_column(String(128))
    created: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    users: Mapped[List["ProjectAccess"]] = relationship("ProjectAccess", back_populates="project")


class AccessLevel(enum.Enum):
    admin = "admin"
    manager = "manager"
    colaborator = "colaborator"
    viewer = "viewer"


class ProjectAccess(UserBase):
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
