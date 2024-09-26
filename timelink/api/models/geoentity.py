"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

from sqlalchemy import Column, String, ForeignKey

from timelink.kleio.utilities import quote_long_text, get_extra_info as gxi, render_with_extra_info as rxi
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

    def to_kleio(self, ident="", ident_inc="  ", self_string=None, show_contained=False, **kwargs) -> str:
        if self_string is None:
            gname = self.groupname
        else:
            gname = self_string
        width = kwargs.get("width", 80)
        obs, extra_info = gxi(self.obs)
        r = f"{gname}${rxi('name',self.name, extra_info=extra_info, initial_indent='',  width=width)}{self.render_id()}"
        if obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(obs.strip(), width=width)}"
        r = super().to_kleio(self_string=r, ident=ident, ident_inc=ident_inc, width=width)
        return r
