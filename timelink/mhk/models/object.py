"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""

# pylint: disable=import-error


from sqlalchemy import Column, String, ForeignKey

from timelink.kleio.utilities import quote_long_text
from timelink.mhk.models.entity import Entity


class Object(Entity):
    __tablename__ = "objects"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
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
        if self.name is None:
            name = ""
        else:
            name = self.name + "/"
        r = f"{self.groupname}${name}{quote_long_text(self.the_type)}/id={self.id}"
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}  /obs={quote_long_text(self.obs)}"
        return r
