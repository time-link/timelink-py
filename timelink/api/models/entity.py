from typing import List, Optional
from datetime import datetime

# for sqlalchemy 2.0 ORM
# see https://docs.sqlalchemy.org/en/20/orm/declarative_config.html
# and https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#orm-declarative-table

from sqlalchemy import ForeignKey, Index  # pylint: disable=import-error
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
    get_extra_info_from_obs,
    render_with_extra_info,
    format_timelink_date as ftld,
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
    links = relationship(
        "Link", back_populates="entity_rel", cascade="all, delete-orphan"
    )

    # this based on
    # https://stackoverflow.com/questions/28843254
    #: list(Entity): list of Entity objects contained in this entity
    contains: Mapped[List["Entity"]] = relationship(
        "Entity",
        backref=backref("contained_by", remote_side="Entity.id"),
        cascade="all",
    )

    # group_models = contains the correspondence between groupname and ORM class
    # Ensure mappings are up to date
    # see self.ensure_mappings()
    # see PomSomMapper.group_to_entity(self)
    group_models = {}

    # group pom classes = contains the correspondence between groupname and PomSomMapper
    # note that classes store here can raise DetachedInstanceError when accessed
    group_pom_classes = {}

    # maps group elements to columns. updated by PomSomMapper.kgroup_to_entity
    # this is a dictionary of dictionaries: first key the group name, second key the element name
    group_elements_to_columns = {"entity": {"id": "id"}}

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
        """Ids of PomSomMapper references by orm classes

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

    def get_column_for_element(self, element: str):
        """Get the column name for a group element"""
        self.update_group_elements_to_columns
        return Entity.group_elements_to_columns.get(self.groupname, {}).get(
            element, None
        )

    def get_element_for_column(self, column: str):
        """Get the element name for a column"""

        self.update_group_elements_to_columns()
        for element, column_name in Entity.group_elements_to_columns.get(
            self.groupname, {}
        ).items():
            if column_name == column:
                return element
        return None

    def update_group_elements_to_columns(self):
        """Update the element to column mappings for this entity"""
        if (
            Entity.group_elements_to_columns.get(self.groupname, None) is None
            or len(  # noqa: W503
                Entity.group_elements_to_columns.get(self.groupname, {})
            )
            == 0  # noqa: W503
        ):
            session = object_session(self)
            if session is None:
                raise ValueError(
                    "Entity must be in a session to update element to columns" "mappings"
                )
                # when a group is added programaically, the element to column mappings
                # the pom_class can be None. In this case, we use the group name
                # as the pom_class
            if self.pom_class is None:
                self.pom_class = self.groupname
                # get the PomSomMapper for this group
            psm = session.get(Entity, self.pom_class)  # <- PomSomMapper
            if psm is None:
                raise ValueError(f"No PomSomMapper found for this group {self.groupname}")
                # get the element to column mappings
            elcol_map: dict = Entity.group_elements_to_columns.get(self.groupname, {})
            for cattr in psm.class_attributes:  # noqa
                elcol_map[cattr.name] = cattr.colname
            Entity.group_elements_to_columns[self.groupname] = elcol_map

    def get_element_names(self):
        """Get the names of the elements for this entity"""
        self.update_group_elements_to_columns()
        return Entity.group_elements_to_columns.get(self.groupname, {}).keys()

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

        This method checks if there is extra information about the entity.
        This is needed because in the source oriented notation each
        value can have a comment and the original wording of the value,
        and also multiple values for a single element/field.

        The way this is managed in the relational database (person oriented model)
        is to store the information as a Json object in the 'extra_info' field.
        A legacy pattern was to store the information in the 'obs' field.

        if an entity has an 'obs' field and that field
        contains the string 'extra_info:' then the rest
        of the field is considered a json representation of
        extra information about the entity. Extra information can
        be comments and original wording of field values.

        This method returns a tuple with the extra information
        as dict and, in the case that the obs field
        contains extra information, a new obs string
        (withou the extra_info part).


        Currently the dictionary has the following structure:

            {'field_name':
                {'comment': text_of_comment,
                 'original': original_wording}}


        """
        extra_info = {}
        if hasattr(self, "obs"):
            obs = getattr(self, "obs", None)
        else:
            obs = None
        if obs is not None and "extra_info:" in obs:
            obs, extra_info = get_extra_info_from_obs(obs)

        if hasattr(self, "extra_info") and self.extra_info is not None:
            extra_info = getattr(self, "extra_info", None)
        return obs, extra_info

    # render related methods
    def description_elements(self):
        """Return a list of elements to be used in the description of the entity"""
        return ["name", "description", "desc", "title", "id"]

    def get_description(self, default=None):
        """Return a descritive name for the entity"""
        desc = None
        for element in self.description_elements():
            if hasattr(self, element):
                desc = getattr(self, element)
                break
        if desc is None:
            desc = default
        return desc

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
        groupname = self.groupname
        if groupname is None:
            groupname = self.pom_class
        if groupname is None:
            groupname = "entity"
        desc = self.get_description()
        if desc is not None:
            r = f"{groupname}${desc}"
        else:
            r = f"{groupname}${self.id}"
        els = self.get_element_names()
        dels = self.description_elements()
        show = sorted(list(set(els) - set(dels)))
        if "obs" in show:
            show.remove("obs")
            show.append("obs")
        for element in show:
            r = f"{r}{self.for_kleio(element, prefix='/', named=True, skip_if_empty=True)}"
        r = r + self.render_id()
        return r

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

    def for_kleio(self, element: str, named=False, prefix="", skip_if_empty=False):
        """Render a specific attribute/column/element of the entity for kleio.

        Check which attribute is requested and return the value
        Checks for extra information for this attribute.

        Extra information can be "comment" or "original"

        if the attribute has a comment, #comment is appended to the value
        if the attribute has an original wording, %original is appended to the value

        """
        # check if the element is a mapped kleio group element
        attr_name = self.get_column_for_element(element)
        if attr_name is None and hasattr(self, element):
            # if not take it as a direct attribute
            # this means the element is a column name like "the_date"
            # and not a group element like "date"
            # but we still the element name to check
            # for extra information
            attr_name = element
            element = self.get_element_for_column(attr_name)

        if hasattr(self, attr_name):
            attr = getattr(self, attr_name)
            if attr is None:
                attr = ""
            else:
                attr = str(attr)  # we need this for enumerations and numbers
            # if the lement is obs that is can cointain extra information
            # that we need to extract and remove from the fied
            obs, extra_info = self.get_extra_info()
            if element == "obs":  # if the element is obs, replace without extra_info
                if obs is not None:
                    attr = obs.strip()
                else:
                    attr = ""
            attr = kleio_escape(attr)
            if element == "date":  # TODO this should test element class not name
                attr = ftld(attr)
            if extra_info is not None and element in extra_info:
                extras = extra_info.get(element, {})
                element_comment = extras.get("comment", None)
                element_original = extras.get("original", None)
                if element_comment is not None:
                    attr = f"{attr}#{kleio_escape(element_comment)}"
                if element_original is not None:
                    attr = f"{attr}%{kleio_escape(element_original)}"
            if skip_if_empty and attr == "":
                return ""
            else:
                return (f"{prefix}{element}=" if named else "") + attr
        else:
            return ""

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


#  Add composite index to speed up
Index("entities_class_group", Entity.pom_class, Entity.groupname)
