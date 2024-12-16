# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .entity import Entity


class Attribute(Entity):
    """represents an attribute of an entity.

    Attributes have a type, a value, a date and an optional observation."""

    __tablename__ = "attributes"

    id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    entity = Column(String, ForeignKey("entities.id"), index=True)
    the_type = Column(String, index=True)
    the_value = Column(String, index=True)
    the_date = Column(String, index=True)
    obs = Column(String)
    the_entity = relationship(
        "Entity",
        foreign_keys=[entity],
        back_populates="attributes",
    )

    __mapper_args__ = {
        "polymorphic_identity": "attribute",
        "inherit_condition": id == Entity.id,
    }

    __table_args__ = (Index("attributes_type_value", "the_type", "the_value"),)

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Attribute(id={sr}, "
            f'entity="{self.entity}", '
            f'the_type="{self.the_type}", '
            f'the_value="{self.the_value}", '
            f'the_date="{self.the_date}"", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        return self.to_kleio(show_contained=False)

    def to_kleio(
        self, ident="", ident_inc="  ", self_string=None, show_contained=False, **kwargs
    ):
        if self.groupname is None:
            myname = "attribute"
        else:
            myname = self.groupname
        r = f"{myname}${self.for_kleio('the_type')}"
        r += f"/{self.for_kleio('the_value')}/"
        r += f"{self.for_kleio('the_date')}"
        obs_el = self.for_kleio("obs", named=True, prefix="", skip_if_empty=True)
        r = f"{r}{obs_el}"
        kleio = super().to_kleio(
            self_string=r,
            show_contained=show_contained,
            ident=ident,
            ident_inc=ident_inc,
            **kwargs,
        )
        return kleio


Entity.attributes = relationship(
    Attribute, foreign_keys=[Attribute.entity], back_populates="the_entity"
)
