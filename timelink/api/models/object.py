"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

from sqlalchemy import Column, String, ForeignKey

from timelink.kleio.utilities import quote_long_text
from .entity import Entity


class Object(Entity):
    """
    Represent an object in the database. Objects are entities that are not people.
    """
    __tablename__ = "objects"

    id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String, index=True)
    the_type = Column(String(32), index=True)
    obs = Column(String)

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

    def __str__(self):
        return self.to_kleio(show_contained=False)

    def to_kleio(self, ident="", ident_inc="  ", width=80, show_contained=True) -> str:
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
