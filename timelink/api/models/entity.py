from typing import List, Optional
from datetime import datetime

# for sqlalchemy 2.0 ORM
# see https://docs.sqlalchemy.org/en/20/orm/declarative_config.html
# and https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#orm-declarative-table

from sqlalchemy import ForeignKey  # pylint: disable=import-error
from sqlalchemy import String  # pylint: disable=import-error
from sqlalchemy import Integer  # pylint: disable=import-error
from sqlalchemy import DateTime  # pylint: disable=import-error
from sqlalchemy import JSON  # pylint: disable=import-error
from sqlalchemy.orm import backref  # pylint: disable=import-error
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column  # pylint: disable=import-error
from sqlalchemy.orm import relationship  # pylint: disable=import-error
from sqlalchemy.orm import object_session  # pylint: disable=import-error
from sqlalchemy import inspect  # pylint: disable=import-error

from timelink.kleio.utilities import (
    kleio_escape,
    get_extra_info,
    render_with_extra_info,
)
from .base_class import Base


class Entity(Base):
    """ORM Model root of the object hierarchy.

    All entities in a Timelink/MHK database have an entry in this table.
    Each entity is associated with a class that allow access to a
    specialization table with more columns for that class.

    This corresponds to the model described as "Joined Table Inheritance"
    in sqlalchemy (see https://docs.sqlalchemy.org/en/14/orm/inheritance.html)

    TODO: specialize TemporalEntity to implement https://github.com/time-link/timelink-kleio/issues/1
            Acts, Sources, Attributes and Relations are TemporalEntities
    """

    __tablename__ = "entities"
    __allow_unmapped__ = True

    #: str: unique identifier for the entity
    id: Mapped[str] = mapped_column(primary_key=True)
    #: str: name of the class. Links to pom_som_mapper class
    # TODO: https://docs.sqlalchemy.org/en/20/orm/declarative_config.html
    pom_class: Mapped[str] = mapped_column(
        "class",
        String,
        # ForeignKey('classes.id', name='fk_entity_class', use_alter=True),
        index=True,
    )
    #: str: id of the entity inside which this occurred.
    inside: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    # id of the source from which this entity was extracted
    the_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    #: int: sequential order of this entity in the source
    the_order = mapped_column(Integer, nullable=True)
    #: int: the nesting level of this entity in the source
    the_level = mapped_column(Integer, nullable=True)
    #: int: line in which the entity occurred in the source
    the_line = mapped_column(Integer, nullable=True)
    #: str: name of the kleio group that produced this entity
    groupname = mapped_column(String, index=True, nullable=True)
    # extra_info a JSON field with extra information about the entity
    extra_info = mapped_column(JSON, nullable=True)
    #: datetime: when this entity was updated in the database
    updated = mapped_column(DateTime, default=datetime.utcnow, index=True)
    #: datetime: when this entity was added to the full text index
    indexed = mapped_column(DateTime, index=True, nullable=True)

    # This is defined in attribute.py
    # Entity.attributes = relationship(
    #   "Attribute", foreign_keys=[Attribute.entity], back_populates="the_entity"
    #   )
    attributes = None

    # These are defined in relation.py
    # rels_in = relationship("Relation", back_populates="dest")
    # rels_out = relationship("Relation", back_populates="org")

    rels_in = None
    rels_out = None

    # This is defined in REntity.py
    # links = relationship("Link", back_populates="entity_rel", cascade="all, delete-orphan")

    links = None

    # this based on
    # https://stackoverflow.com/questions/28843254
    #: list(Entity): list of Entity objects contained in this entity
    contains: Mapped[List["Entity"]] = relationship(
        "Entity",
        backref=backref("contained_by", remote_side="Entity.id"),
        cascade="all",
    )

    # group_models = contains the correspondence between groupname and ORM class
    group_models = {}

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
    def get_orm_for_group(cls, groupname: str):
        """
        Entity.get_orm_for_group("acts")

        will return the ORM class handling a given group
        """
        return cls.group_models.get(groupname, None)

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
    def get_entity(cls, eid: str, session=None):
        """
        Get an Entity from the database. The object returned
        will be of the ORM class defined by mappings.
        :param id: id of the entity
        :param session: current session
        :return: an Entity object of the proper class for the mapping
        """
        entity = session.get(Entity, eid)
        if entity is not None:
            if entity.pom_class != "entity":
                orm_class = Entity.get_orm_for_pom_class(entity.pom_class)
                object_for_id = session.get(orm_class, eid)
                return object_for_id
            else:
                return entity
        else:
            return None

    def add_attribute(self, attribute):
        """Add an attribute to the entity"""
        if attribute.inside is None:
            attribute.inside = self.id
        self.attributes.append(attribute)

    def add_relation(self, relation):
        """Add a relation to the entity"""
        if relation.inside is None:
            relation.inside = self.id
        if relation.origin is None or self.id == relation.origin:
            # no origin, this is the origin
            relation.origin = self.id
            self.rels_out.append(relation)
        elif relation.destination is None or self.id == relation.destination:
            # no destination, this is the destination
            relation.destination = self.id
            self.rels_in.append(relation)
        else:
            raise ValueError("Relation does not belong to this entity")

    def with_extra_info(self):
        """Returns a copy of the entity with field values rendered with extra information

        Extra_info is current stored as json in the obs field of the entity, or
        in the extra_info field of the entity. The extra_info field is a json field.
        """
        # the the current session
        session = object_session(self)
        if session is None:
            raise ValueError("Entity must be in a session to get extra info")
        # create a new object of the same class
        new_entity = self.__class__()
        mapper = inspect(type(self))
        field_to_column = {
            col.key: col.columns[0].name for col in list(mapper.column_attrs)
        }
        obs, extra_info = self.get_extra_info()
        for name, __column in field_to_column.items():
            nvalue = render_with_extra_info(name, getattr(self, name), extra_info)
            setattr(new_entity, name, nvalue)

        setattr(new_entity, "obs", obs)  # noqa

        return new_entity

    def get_extra_info(self) -> tuple[str, dict]:
        """Return a dictionatry with extra information about this entity or None

        if entity has an 'obs' field and that field
        contains the string 'extra_info:' then the rest
        of the field is considered a json representation of
        extra information about the entity. Extra information can
        be comments and original wording of field values.

        This method returns a tuple with the new obs string
        (withou the extra_info part) and a dictionary with
        the extra information.


        Currently the dictionary has the following structure:

            {'field_name': {'comment': text_of_comment, 'original': original_wording}}
        """
        if hasattr(self, "extra_info"):
            extra_info = getattr(self, "extra_info", None)
            if extra_info is not None:
                return getattr(self, "obs", None), extra_info
        obs = getattr(self, "obs", None)
        return get_extra_info(obs)

    def __repr__(self):
        return (
            f'Entity(id="{self.id}", '
            f'pom_class="{self.pom_class}", '
            f'inside="{self.inside}", '
            f"the_source={self.the_source}, "
            f"the_order={self.the_order}, "
            f"the_level={self.the_level}, "
            f"the_line={self.the_line}, "
            f'groupname="{self.groupname}", '
            f"updated={self.updated}, "
            f"indexed={self.indexed})"
        )

    def __str__(self):
        if self.groupname is None:
            return f"{self.pom_class}${kleio_escape(self.id)}"
        return f"{self.groupname}${kleio_escape(self.id)}/type={kleio_escape(self.pom_class)}"

    def render_id(self):
        """Return the id of the entity in a kleio format

        Does not return the id if it starts with an underscore"""
        if self.id[:1] == "_":
            return ""
        else:
            return f"/id={self.id}"

    def dated_bio(self) -> dict:
        """Return the atributes and relations of the entity grouped by date

        Returns a dictionary with the date as key and a list of attributes and relations as value

        """
        bio = dict()

        if self.rels_in is not None:
            for rel in self.rels_in:
                date = rel.the_date
                this_date_list = bio.get(date, [])
                this_date_list.append(rel)
                bio[date] = this_date_list
        if self.rels_out is not None:
            for rel in self.rels_out:
                date = rel.the_date
                this_date_list = bio.get(date, [])
                this_date_list.append(rel)
                bio[date] = this_date_list
        if self.attributes is not None:
            for attr in self.attributes:
                date = attr.the_date
                this_date_list = bio.get(date, [])
                this_date_list.append(attr)
                bio[date] = this_date_list
        return bio

    def is_inbound_relation(self, relation):
        """Check if the relation is inbound to this entity.

        Override in real entities or other special cases
        """
        return relation.destination == self.id

    # Handling of updating entities already in the databse
    # This should be overriden in the different models.
    def get_update_context(Entity, session, **kwargs):
        """return the context of this entity prior to an update.

        Updates are done by deleting and reinserting entities,
        and all their contained entities in the scope of a source.
        If an entity has links and dependencies with entities not
        in the same source, then its possible that those links will be affected
        by foreign keys constraints like "on delete cascade".

        This method saves the extra source context of this entity before
        it is replaced so that it can be restored by the sister
        function restore_update_context.

        Usage:
                ent = session.get(Entity,eid).
                new_ent = Entity(...)
                ctxt = ent.get_update_context(ent,session)
                session.delete(ent.id)
                session.add(new_ent)
                new_ent.restore_update_contex(ctxt,session)

        In the base person oriented model the only external context of entities
        are normally those related to record linking and involves  "same as" links
        between sources, that are recorded as relations `identification/same as`
        where origin and destination are not in the same source,
        and generate entries in the `links` table where the
        entity referred in the link is not in the same file as the link (both are
        generated by "sameas" element in groups.

        Note that nothing prevents that a "normal" user entered relation refers
        to a destination outside the source (normally VIPs).

        Early Soure records had a bit of this
        before it became good practice to always record
        a local entity for the destination of relations
        and use "sameas" to link the local entity to the
        external one.

        Currently sqlalchemy ORM sets the destination of these relations to None and
        removed the link row when it refers to an entity that was deleted.

        Note that it not useful to save the link, because it contains a pair RealId,
        occurrenceID, and the RealId might have changed with reimport. So it must
        be regenerated by calling REntity.same_as(...)

        """

        return None

    #
    def restore_update_context(self, ctxt, session):
        """restore the context of this entity after an update.
        See get_update_context for details
        """
        return None

    def to_kleio(
        self, self_string=None, show_contained=True, ident="", ident_inc="  ", **kwargs
    ):
        """conver the entity to a kleio string

        Args:
            self_string: the string to be used to represent the entity
            show_contained: if True, contained entities are also converted to kleio
            ident: initial identation
            ident_inc: identation increment
            kwargs: additional arguments to be passed to contained entities"""
        if self_string is None:
            s = f"{ident}{str(self)}"
        else:
            s = f"{ident}{self_string}"

        contained_entities = list(
            set(self.contains)
            - set(self.rels_in)  # noqa: W503
            - set(self.rels_out)  # noqa: W503
            - set(self.attributes)  # noqa: W503
        )
        bio = self.dated_bio()
        sorted_keys = sorted(bio.keys())
        for date in sorted_keys:
            date_list = bio[date]
            for bio_item in date_list:
                bio_item_xi = bio_item
                if bio_item.pom_class == "relation":

                    kwargs["outgoing"] = not self.is_inbound_relation(bio_item)
                    if self.is_inbound_relation(bio_item):
                        if bio_item.the_type == "function-in-act":
                            # we don't render inbound function-in-act relations
                            # because they are redundant with contained entities
                            continue

                bio_itemk = bio_item_xi.to_kleio(
                    ident=ident + ident_inc, ident_inc=ident_inc, **kwargs
                )

                if bio_itemk != "":
                    s = f"{s}\n{bio_itemk}"

        # sort by the_order
        if show_contained and contained_entities is not None:
            contained_entities.sort(
                key=lambda x: x.the_order if x.the_order is not None else 999999
            )
            for inner in contained_entities:
                innerk = inner.to_kleio(
                    ident=ident + ident_inc, ident_inc=ident_inc, **kwargs
                )
                if innerk != "":
                    s = f"{s}\n{innerk}"
        return s
