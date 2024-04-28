# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey

from timelink.mhk.models.entity import Entity
from timelink.kleio.utilities import quote_long_text


class Person(Entity):
    """Represents a person."""

    __tablename__ = "persons"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    name = Column(String, index=True)
    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    name = Column(String)
    sex = Column(String(1))
    obs = Column(String)

    __mapper_args__ = {"polymorphic_identity": "person"}

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Person(id={sr}, "
            f'name="{self.name}", '
            f'sex="{self.sex}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        r = f"{self.groupname}${quote_long_text(self.name)}/{quote_long_text(self.sex)}/id={quote_long_text(self.id)}"
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r
