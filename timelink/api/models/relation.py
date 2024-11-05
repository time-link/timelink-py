import warnings

# pylint: disable=import-error
from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship

from timelink.kleio.utilities import (
    kleio_escape,
    quote_long_text,
    format_timelink_date as ftld,
)
from .entity import Entity


class Relation(Entity):
    """represents a relation between two entities.

    Relations have a type, a value, a date and an optional observation.

    Args:
        id (str): the id of the relation
        origin (str): the id of the origin entity
        destination (str): the id of the destination entity
        the_type (str): the type of the relation
        the_value (str): the value of the relation
        the_date (str): the date of the relation
        obs (str): an observation about the relation

    Also, for the entity super class:
        groupname (str): the name of the group
        inside (str): the id of the containing entity
        the_line (str): the line of the entity in the source
        the_level (str): the level of the entity in the source
        the_order (str): the order of the entity in the source

    """

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
        if self.dest is None:
            warnings.warn("Missing destination for relation", UserWarning, stacklevel=2)
            return None
        return self.dest.pom_class

    @property
    def org_class(self):
        return self.org.pom_class

    @property
    def dest_name(self):
        if self.dest_class is None:
            return ""
        elif self.dest_class == "person" or self.dest_class == "object":
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
            f'the_date="{self.the_date}", '
            f"obs={self.obs}"
            f")"
        )

    def __str__(self):
        return self.to_kleio()

    def to_kleio(self, ident="", **kwargs):  # pylint: disable=arguments-differ

        outgoing = kwargs.get("outgoing", True)
        if outgoing:
            if self.the_type == "function-in-act":
                function = self.the_value
                act_type = self.dest.groupname
                act_date = self.dest.the_date
                act_id = self.dest.id

                s = f"{ident}rel$function-in-act/{function}/{act_type}/{act_id}/{ftld(act_date)}"
                if self.the_line is not None:
                    s += f"/obs=line: {self.the_line}"
                return s

            if self.the_type == "identification":

                return f"{ident}rel$identification/{self.the_value}/{self.dest_name}/{self.destination}/{ftld(self.the_date)}"

            if self.dest is not None:
                if self.dest.pom_class in [
                    "person",
                    "object",
                    "geoentity",
                ]:
                    relname = self.dest.name
                else:
                    relname = self.dest.groupname
            else:
                relname = "*missing*"
            label = "rel"
        else:  # incoming relation

            if self.org is not None and self.org.pom_class in [
                "person",
                "object",
                "geoentity",
            ]:
                relname = self.org.name
            else:
                relname = self.org.groupname
            label = "<rel"

        r = (
            f"{ident}{label}${kleio_escape(self.the_type)}/"
            f"{quote_long_text(self.the_value)}/"
            f"{kleio_escape(relname)}/{self.origin}/{ftld(self.the_date)}"
        )
        if self.obs is not None and len(self.obs.strip()) > 0:
            r = f"{r}/obs={quote_long_text(self.obs)}"
        return r


Entity.rels_out = relationship(
    "Relation", foreign_keys=[Relation.origin], back_populates="dest"
)

Entity.rels_in = relationship(
    "Relation", foreign_keys=[Relation.destination], back_populates="org"
)
