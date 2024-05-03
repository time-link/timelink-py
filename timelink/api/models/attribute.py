# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .entity import Entity
from timelink.kleio.utilities import quote_long_text


class Attribute(Entity):
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

    def to_kleio(self, ident="", ident_inc="  ", width=80) -> str:
        r = f"{self.groupname}${quote_long_text(self.the_type)}"
        r += f"/{quote_long_text(self.the_value)}/"
        r += f"{self.the_date}"
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        kleio = super().to_kleio(
            self_string=r, ident=ident, ident_inc=ident_inc, width=width
        )
        return kleio


Entity.attributes = relationship(
    "Attribute", foreign_keys=[Attribute.entity], back_populates="the_entity"
)
