# pylint: disable=import-error
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from timelink.kleio.utilities import kleio_escape, quote_long_text
from .entity import Entity


class Relation(Entity):
    __tablename__ = "relations"

    id = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    # rel_entity = relationship("Entity",
    #                   foreign_keys='id',back_populates='rel')
    origin = Column(String, ForeignKey("entities.id"), index=True)
    org = relationship(Entity, foreign_keys=[origin], back_populates="rels_out")

    destination = Column(String, ForeignKey("entities.id"), index=True)
    dest = relationship("Entity", foreign_keys=[destination], back_populates="rels_in")
    the_type = Column(String, index=True)
    the_value = Column(String, index=True)
    the_date = Column(String, index=True)
    obs = Column(String)

    __mapper_args__ = {
        "polymorphic_identity": "relation",
        "inherit_condition": id == Entity.id,
    }

    __table_args__ = (Index("relations_type_value", "the_type", "the_value"),)

    @property
    def dest_class(self):
        return self.dest.pom_class

    @property
    def org_class(self):
        return self.org.pom_class

    @property
    def dest_name(self):
        if self.dest_class == "person" or self.dest_class == "object":
            return self.dest.name
        else:
            return self.dest.groupname

    @property
    def org_name(self):
        if self.org_class == "person" or self.org_class == "object":
            return self.org.name
        else:
            return self.org.groupname

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
        if self.dest is not None and self.dest.pom_class == "person":
            r = (
                f"rel${kleio_escape(self.the_type)}/{quote_long_text(self.the_value)}/{kleio_escape(self.dest.name)}"
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

    def to_kleio(self, **kwargs):
        if self.the_type == "function-in-act":
            return ""
        else:
            # call to_kleio from the parent class
            return super().to_kleio(**kwargs)


Entity.rels_out = relationship(
    "Relation", foreign_keys=[Relation.origin], back_populates="dest"
)

Entity.rels_in = relationship(
    "Relation", foreign_keys=[Relation.destination], back_populates="org"
)
