from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
)  # pylint: disable=import-error
from sqlalchemy.orm import relationship, backref  # pylint: disable=import-error

from timelink.kleio.utilities import kleio_escape
from timelink.mhk.models.base_class import Base


class Entity(Base):
    """ORM Model root of the object hierarchy.

     All entities in a Timelink/MHK database have an entry in this table.
     Each entity is associated with a class that allow access to a
     specialization table with more columns for that class.

    This corresponds to the model described as "Joined Table Inheritance"
    in sqlalchemy (see https://docs.sqlalchemy.org/en/14/orm/inheritance.html)
    """

    __tablename__ = "entities"

    #: str: unique identifier for the entity
    id = Column(String, primary_key=True)
    #: str: name of the class. Links to pom_som_mapper class
    pom_class = Column(
        "class", String, ForeignKey("classes.id", use_alter=True), index=True
    )
    #: str: id of the entity inside which this occurred.
    inside = Column(String, ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    #: int: sequential order of this entity in the source
    the_order = Column(Integer)
    #: int: the nesting level of this entity in the source
    the_level = Column(Integer)
    #: int: line in which the entity occurred in the source
    the_line = Column(Integer)
    #: str: name of the kleio group that produced this entity
    groupname = Column(String, index=True)
    #: datetime: when this entity was updated in the database
    updated = Column(DateTime, default=datetime.utcnow, index=True)
    #: datetime: when this entity was added to the full text index
    indexed = Column(DateTime, index=True)

    # These are defined in relation.py
    # rels_in = relationship("Relation", back_populates="dest")
    # rels_out = relationship("Relation", back_populates="org")
    # this based on
    # https://stackoverflow.com/questions/28843254
    #: list(Entity): list of Entity objects contained in this entity
    contains = relationship(
        "Entity",
        backref=backref("contained_by", remote_side="Entity.id"),
        cascade="all",
    )

    # see https://docs.sqlalchemy.org/en/14/orm/inheritance.html
    # To handle non mapped pom_class
    #      see https://github.com/sqlalchemy/sqlalchemy/issues/5445
    #
    #    __mapper_args__ = {
    #       "polymorphic_identity": "entity",
    #    "polymorphic_on": case(
    #        [(type.in_(["parent", "child"]), type)], else_="entity"
    #    ),
    #
    #  This defines what mappings do exist
    # [aclass.__mapper_args__['polymorphic_identity']
    #              for aclass in Entity.__subclasses__()]

    __mapper_args__ = {
        "polymorphic_identity": "entity",
        "polymorphic_on": pom_class,
    }

    @classmethod
    def get_subclasses(cls):
        """Get the subclasses of Entity"""
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def get_orm_entities_classes(cls):
        """Currently defined ORM classes that extend Entity
         (including Entity itself)


        Returns:
             list: List of ORM classes
        """
        sc = list(Entity.get_subclasses())
        sc.append(Entity)
        return sc

    @classmethod
    def get_som_mapper_ids(cls):
        """Ids of SomPomMapper references by orm classes

        Returns:
             List[str]: List of strings
        """
        return [
            aclass.__mapper_args__["polymorphic_identity"]
            for aclass in Entity.get_orm_entities_classes()
        ]

    @classmethod
    def get_tables_to_orm_as_dict(cls):
        """
        Return a dict with table name as key and ORM class as value
        """
        return {
            ormclass.__mapper__.local_table.name: ormclass
            for ormclass in Entity.get_orm_entities_classes()
        }

    @classmethod
    def get_som_mapper_to_orm_as_dict(cls):
        """
        Return a dict with pom_class id as key and ORM class as value
        """
        sc = Entity.get_orm_entities_classes()
        return {ormclass.__mapper__.polymorphic_identity: ormclass for ormclass in sc}

    @classmethod
    def get_orm_for_table(cls, table: String):
        """
        Entity.get_orm_for_table("acts")

        will return the ORM class handling the "acts" table
        """
        return cls.get_tables_to_orm_as_dict().get(table, None)

    @classmethod
    def get_orm_for_pom_class(cls, pom_class: str):
        """
        Entity.get_orm_for_pom_class("act")

        will return the ORM class corresponding to the pom_class "act"
        """
        return cls.get_som_mapper_to_orm_as_dict().get(pom_class, None)

    @classmethod
    def get_entity(cls, id: str, session=None):
        """
        Get an Entity from the database. The object returned
        will be of the ORM class defined by mappings.
        :param id: id of the entity
        :param session: current session
        :return: an Entity object of the proper class for the mapping
        """
        entity = session.get(Entity, id)
        if entity is not None:
            if entity.pom_class != "entity":
                orm_class = Entity.get_orm_for_pom_class(entity.pom_class)
                object_for_id = session.get(orm_class, id)
                return object_for_id
            else:
                return entity
        else:
            return None

        return entity

    def __repr__(self):
        return (
            f'Entity(id="{self.id}", '
            f'pom_class="{self.pom_class}",'
            f'inside="{self.inside}", '
            f"the_order={self.the_order}, "
            f"the_level={self.the_level}, "
            f"the_line={self.the_line}, "
            f'groupname="{self.groupname}", '
            f"updated={self.updated}, "
            f"indexed={self.indexed},"
            f")"
        )

    def __str__(self):
        return f"{self.groupname}${kleio_escape(self.id)}/type={kleio_escape(self.pom_class)}"

    def to_kleio(self, ident="", ident_inc="  "):
        s = f"{ident}{str(self)}"
        for inner in self.contains:
            innerk = inner.to_kleio(ident=ident + ident_inc, ident_inc=ident_inc)
            s = f"{s}\n{innerk}"
        return s
