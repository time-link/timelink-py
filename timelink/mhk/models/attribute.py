from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship

from timelink.mhk.models.base import Entity


class Attribute(Entity):
    __tablename__ = "attributes"

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    entity = Column(String, ForeignKey("entities.id"))
    the_type = Column(String)
    the_value = Column(String)
    the_date = Column(String)
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
        r = f"{self.groupname}${self.the_type}/{self.the_value}/{self.the_date}"  # noqa
        if self.obs is not None:
            r = f"{r}/obs={self.obs}"
        return r


Entity.attributes = relationship(
    "Attribute", foreign_keys=[Attribute.entity], back_populates="the_entity"
)
