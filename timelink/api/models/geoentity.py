"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

from sqlalchemy import Column, String, ForeignKey

from timelink.kleio.utilities import quote_long_text
from .entity import Entity


class Geoentity(Entity):
    """ represents a geographical entity."""

    __tablename__ = "geoentities"

    id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String, index=True)
    the_type = Column(String(32), nullable=True)
    obs = Column(String)

    __mapper_args__ = {"polymorphic_identity": "geoentity"}

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Geoentity(id={sr}, "
            f'name="{self.name}", '
            f'the_type="{self.the_type}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        return self.to_kleio(show_contained=False)

    def to_kleio(self, self_string=None, show_contained=False, ident="", ident_inc="  ", width=80, **kwargs) -> str:

        if self_string is None:
            if self.name is None:
                name = ""
            else:
                name = self.name + "/"
            r = f"{self.groupname}${name}{quote_long_text(self.the_type, width=width)}{self.render_id()}"
            if self.obs is not None and len(self.obs.strip()) > 0:
                self_string = f"{r}/obs={quote_long_text(self.obs.strip(), width=width)}"
        r = super().to_kleio(self_string=self_string, ident=ident, ident_inc=ident_inc,
                             show_contained=show_contained, width=width)
        return r
