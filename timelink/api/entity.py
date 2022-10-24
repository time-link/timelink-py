from typing import Optional

from sqlmodel import Field, SQLModel

class Entity(SQLModel, table=True):
    id = Optional[str] = Field(default=None, primar_key=True)
    description = str,
    the_class = str,
    inside: Optional[str] = None,
    the_order: Optional[int] = None,
    the_level = Optional[int] = None,
    the_line = Optional[int] = None,
    groupname = Optional[str] = None
   