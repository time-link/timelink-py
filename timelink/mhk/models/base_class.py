# Base class, all modules must import this to share Metadata
# for 2.0 migration see https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#whatsnew-20-orm-declarative-typing

from typing import Any
from sqlalchemy.orm import DeclarativeBase  # pylint: disable=import-error
from sqlalchemy.orm import declared_attr  # pylint: disable=import-error


class Base(DeclarativeBase):
    """Base class, all modules must import this to share Metadata"""

    __allow_unmapped__: bool = True  # see https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-step-six
    __table_args__: Any = {"extend_existing": True}

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()
