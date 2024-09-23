# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from timelink.kleio.utilities import quote_long_text, get_extra_info, render_with_extra_info
from .entity import Entity


class Attribute(Entity):
    """ represents an attribute of an entity.

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

    def to_kleio(self, show_contained=False, ident="", ident_inc="  ", **kwargs) -> str:
        _ = show_contained  # unused
        obs, extra_info = get_extra_info(self.obs)
        r = f"{self.groupname}${quote_long_text(self.the_type)}"
        r += f"/{render_with_extra_info('value', self.the_value, extra_info=extra_info, **kwargs)}/"
        r += f"{render_with_extra_info('the_date', self.the_date, extra_info=extra_info, **kwargs)}"
        if obs is not None and len(obs.strip()) > 0:
            r = f"{r}/obs={render_with_extra_info('obs', obs, extra_info=extra_info, **kwargs)}"
        kleio = super().to_kleio(
            self_string=r,
            show_contained=show_contained,
            ident=ident,
            ident_inc=ident_inc,
            **kwargs
        )
        return kleio


Entity.attributes = relationship(
    "Attribute", foreign_keys=[Attribute.entity], back_populates="the_entity"
)
