"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

from typing import Optional
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped

from timelink.kleio.utilities import quote_long_text
from .entity import Entity


class Object(Entity):
    """
    Represent an object in the database. Objects are entities that are not people.
    """
    __tablename__ = "objects"

    id: Mapped[str] = mapped_column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, index=True)
    the_type: Mapped[str] = mapped_column(String(32), index=True)
    obs: Mapped[Optional[str]] = mapped_column(String)

    __mapper_args__ = {"polymorphic_identity": "object"}

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Object(id={sr}, "
            f'name="{self.name}", '
            f'the_type="{self.the_type}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__XX(self):
        return self.to_kleio(show_contained=False)

    def to_kleio_xx(self, ident="", ident_inc="  ", width=80, show_contained=True, **kwargs) -> str:
        if self.name is None:
            name = ""
        else:
            name = self.name + "/"
        r = f"{self.groupname}${name}{quote_long_text(self.the_type, width=width)}{self.render_id()}"
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs.strip(), width=width)}"
        r = super().to_kleio(self_string=r,
                             ident=ident,
                             ident_inc=ident_inc,
                             width=width,
                             show_contained=show_contained)
        return r
