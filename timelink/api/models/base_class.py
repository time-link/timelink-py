""" Base class, all modules must import this to share Metadata

   for 2.0 migration see:
   https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#whatsnew-20-orm-declarative-typing

"""

from typing import Any
from sqlalchemy import MetaData  # pylint: disable=import-error
from sqlalchemy.orm import DeclarativeBase  # pylint: disable=import-error
from sqlalchemy.orm import declared_attr  # pylint: disable=import-error


naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_`%(constraint_name)s`",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class, all modules must import this to share Metadata"""

    # see https://alembic.sqlalchemy.org/en/latest/naming.html#naming-conventions
    metadata = MetaData(naming_convention=naming_convention)

    # see https://docs.sqlalchemy.org/en/20/changelog/migration_20.html#migration-20-step-six
    __allow_unmapped__: bool = True

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        return cls.__name__.lower()
