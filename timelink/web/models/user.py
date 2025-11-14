from datetime import datetime
from typing import List, Optional
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

UserBase = declarative_base()


class UserProperty(UserBase):
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


class User(UserBase):
    """
    Attributes:
        id (int): Primary key, autoincrement.
        name (str): Required.
        nickname (str): Optional.
        email (str): Required, unique.
        hashed_password (str): Optional.
        disabled (bool): Optional, default is False.
        is_admin (bool): Whether the user is a site admin or not, default is False
        created (datetime): Required, default is now.
        updated (datetime): Optional, default is now, updated at now.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=False)
    nickname: Mapped[Optional[str]] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(unique=True)
    is_admin: Mapped[bool] = mapped_column(default=False)

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
            f"nickname={self.nickname}, "
            f"created={self.created}, "
            f"updated={self.updated}, "
            f"properties={sproperties})"
        )
