# pylint: disable=import-error

from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from timelink.kleio.utilities import kleio_escape, quote_long_text
from timelink.mhk.models.entity import Entity


class Relation(Entity):
    """Represents a relation between two entities."""

    __allow_unmapped__ = True
    __tablename__ = "relations"
    __table_args__ = {"extend_existing": True}

    id = Column(String, ForeignKey("entities.id"), primary_key=True)
    # rel_entity = relationship("Entity",
    #                   foreign_keys='id',back_populates='rel')
    origin = Column(String, ForeignKey("entities.id"), index=True)
    # org = relationship(Entity, foreign_keys=[origin],
    #                   back_populates='rels_out')

    destination = Column(String, ForeignKey("entities.id"), index=True)
    # dest = relationship("Entity", foreign_keys=[destination],
    #                    back_populates="rels_in")
    the_type = Column(String, index=True)
    the_value = Column(String, index=True)
    the_date = Column(String, index=True)
    obs = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": "relation",
        "inherit_condition": id == Entity.id,
    }

    __table_args__ = (Index("relations_type_value", "the_type", "the_value"),)

    def __repr__(self):
        sr = super().__repr__()
        return (
            f"Relation(id={sr}, "
            f'origin="{self.origin}", '
            f'destination="{self.destination}", '
            f'the_type="{self.the_type}", '
            f'the_value="{self.the_value}", '
            f'the_date="{self.the_date}"", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        if (
            self.dest is not None and self.dest.pom_class == "person"
        ):  # pylint: disable=no-member
            r = (
                f"rel${kleio_escape(self.the_type)}/"
                f"{quote_long_text(self.the_value)}/"
                f"{kleio_escape(self.dest.name)}"  # pylint: disable=no-member
                f"/{self.destination}/{self.the_date}"
            )
        else:
            r = (
                f"rel${self.the_type}/{quote_long_text(self.the_value)}/"
                f"{self.destination}/{self.the_date}"
            )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r


Entity.rels_out = relationship(
    "Relation", foreign_keys=[Relation.origin], backref="dest"
)

Entity.rels_in = relationship(
    "Relation", foreign_keys=[Relation.destination], backref="org"
)
