
# pyright: reportUnnecessaryTypeIgnoreComment=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false

from datetime import datetime, timezone

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

from typing import Optional, List


class Entity(Base):
    """ORM Model root of the object hierarchy.

    All entities in a Timelink/MHK database have an entry in this table.
    Each entity is associated with a class that allow access to a
    specialization table with more columns for that class.

    This corresponds to the model described as "Joined Table Inheritance"
    in sqlalchemy (see https://docs.sqlalchemy.org/en/14/orm/inheritance.html)

    This class also provides methods to manage the association between
    groups and ORM classes. This is needed because the ORM classes
    are created dynamically based on the mappings defined in the
    PomSomMapper class and during import diferent Kleio groups
    are imported associated with different classes.

    TODO: specialize TemporalEntity to implement https://github.com/time-link/timelink-kleio/issues/1
            Acts, Sources, Attributes and Relations are TemporalEntities
    """

    __tablename__ = "entities"  # type: ignore
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
    # For each column of the entity, the value is a dictionary with the following keys:
    # 'class': {'db_column_name': 'class',
    #         'kleio_element_class': 'class',
    #         'kleio_element_name': 'class'},
    # 'date': {'db_column_name': 'the_date',
    #         'kleio_element_class': 'date',
    #         'kleio_element_name': 'date'},
    # 'entity': {'db_column_name': 'entity',
    #             'kleio_element_class': 'entity',
    #             'kleio_element_name': 'entity'},
    # 'id': {'db_column_name': 'id',
    #         'kleio_element_class': 'id',
    #         'kleio_element_name': 'id'},
    # 'type': {'db_column_name': 'the_type',
    #         'kleio_element_class': 'type',
    #         'kleio_element_name': 'tipo'},
    # 'value': {'comment': '@wikidata:Q1171',
    #         'db_column_name': 'the_value',
    #         'kleio_element_class': 'value',
    #         'kleio_element_name': 'valor'}}
    extra_info = mapped_column(JSON, nullable=True)
    #: datetime: when this entity was updated in the database
    updated = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    # #: datetime: when this entity was indexed used with updated to reindex entities
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

    __mapper_args__ = {
        "polymorphic_identity": "entity",
        "polymorphic_on": pom_class,
    }

    # == non persistent attributes ==
    # this ORM class was dynamically created
    # by the PomSomMapper.ensure_mapping
    __is_dynamic__: bool = False

    # is_active: this signals if the class is active
    # a class can be inactive if the app attached
    # to a new database where this class is not used
    # only applies to dynamic classes
    # set to false by PomSomMapper.remove_mapping()
    __is_active__: bool = True

    # group_models = contains the correspondence between groupname and ORM class
    # Ensure mappings are up to date
    # see PomSomMapper.ensure_mappings()
    # see PomSomMapper.group_to_entity(self)
    group_models: dict = {}

    # maps group elements to columns. updated by PomSomMapper.kgroup_to_entity
    # this is a dictionary of dictionaries: first key the group name, second key the element name
    group_elements_to_columns: dict[str, dict[str, str]] = {"entity": {"id": "id"}}

    @classmethod
    def reset_cache(cls):
        """Reset the group_models and group_elements_to_columns cache"""
        cls.group_models = dict()
        cls.group_elements_to_columns = {"entity": {"id": "id"}}

    @classmethod
    def get_subclasses(cls):
        """Get the subclasses of Entity"""
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def is_dynamic(cls):
        """Return True if this class was created by a dynamic mapping

        Dynamic mappings are mappings that are created during the import
        of a Kleio group.
        """
        return getattr(cls, "__is_dynamic__", False)

    @classmethod
    def set_as_dynamic(cls):
        """Set this class as dynamic
        Dynamic mappings are mappings that are created during the import
        of a Kleio group.
        """
        cls.__is_dynamic__ = True

    @classmethod
    def get_orm_models(cls):
        """Currently defined ORM classes that extend Entity
        (including Entity itself)


        Returns:
            list: List of ORM classes
        """
        sc = list(Entity.get_subclasses())
        return [Entity] + sc

    @classmethod
    def get_dynamic_models(cls):
        """Dynamically defined ORM classes that extend Entity

        Dynamic models are models that are created during the import
        of Kleio groups.


        Returns:
            list: List of ORM classes
        """

        return [orm for orm in cls.get_orm_models() if orm.is_dynamic()]

    @classmethod
    def get_som_mapper_ids(cls):
        """Ids of PomSomMapper references by orm classes

        Returns:
            List[str]: List of strings
        """
        return [
            aclass.__mapper_args__["polymorphic_identity"]
            for aclass in cls.get_orm_models()
        ]

    @classmethod
    def get_tables_to_orm_as_dict(cls):
        """
        Return a dict with table name as key and ORM class as value
        """
        return {
            ormclass.__mapper__.local_table.name: ormclass  # type: ignore
            for ormclass in cls.get_orm_models()
        }

    @classmethod
    def get_tables_to_dynamic_orm_as_dict(cls):
        """
        Return a dict with table name as key and ORM class as value
        """
        return {
            ormclass.__mapper__.local_table.name: ormclass
            for ormclass in cls.get_dynamic_models()
        }

    @classmethod
    def get_orm_table_names(cls):
        """ Return the names of tables associated with ORM models"""
        return [str(table) for table in cls.get_tables_to_orm_as_dict().keys()]

    @classmethod
    def get_dynamic_orm_table_names(cls):
        """ Return the names of tables associated with ORM models"""
        return [str(table) for table in cls.get_tables_to_dynamic_orm_as_dict().keys()]

    @classmethod
    def get_orm_tables(cls):
        """ Return the  table objects associated with ORM models"""
        return [ormclass.__mapper__.local_table for ormclass in Entity.get_orm_models()]

    @classmethod
    def get_group_models(cls) -> dict:
        """ Return a dictionary of group models

        The keys are group names and the values are ORM
        Models.
        """
        return cls.group_models

    @classmethod
    def get_groups_for_orm(cls, orm: str):
        """ get the list of groups that map to this model

        Args:
           orm (str):  id of a orm model
        """
        return [group for (group, orm)
                in cls.get_group_models().items()
                if orm.id == str]

    @classmethod
    def get_orm_for_group(cls, groupname: str):
        """
        Entity.get_orm_for_group("acts")

        will return the ORM class handling a given group
        """
        meta_group_models = cls.get_group_models()
        if meta_group_models is not None:
            return meta_group_models.get(groupname, None)
        else:
            raise ValueError(f"{groupname} is not associated with any ORM Model class")

    @classmethod
    def set_orm_for_group(cls, groupname: str, ormclass):
        cls.group_models[groupname] = ormclass

    @classmethod
    def clear_group_models_cache(cls):
        """Clear cached association between groups and ormclass"""
        cls.group_models = dict()

    @classmethod
    def get_som_mapper_to_orm_as_dict(cls):
        """
        Return a dict with pom_class id as key and ORM class as value
        """
        sc = Entity.get_orm_models()
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
    def get_entity(cls, eid: str, session):
        """
        Get an Entity from the database. The object returned
        will be of the ORM class defined by mappings.
        :param id: id of the entity
        :param session: current session
        :return: an Entity object of the proper class for the mapping
        """
        if session is None:
            raise ValueError("Entity.get_entity() requires a session")
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

    @property
    def description(self) -> str:
        return self.get_description(default=self.groupname)

    def get_column_for_element(self, element: str):
        """Get the column name for a group element"""
        self.update_group_elements_to_columns()
        column = Entity.group_elements_to_columns.get(self.groupname, {}).get(
            element, None)
        if column is None and self.extra_info :
            names = {el['kleio_element_name']: el['entity_column_class'] for el in self.extra_info.values()}
            column = names.get(element, None)
        else:  # we have no information about the element to colunn mapping, so we use the element name
            column = element
        return column

    def get_element_for_column(self, column: str):
        """Get the kleio element name for a column"""

        self.update_group_elements_to_columns()
        extra_info = getattr(self, "extra_info", None)
        element_name = None
        if extra_info is not None:
            col_extra_info = extra_info.get(column, None)
            if col_extra_info is not None:
                element_name = col_extra_info.get("kleio_element_name", None)
        if element_name is not None:
            return element_name
        # if we didn't find it in extra_info, look in the group_elements_to_columns
        for element, column_name in Entity.group_elements_to_columns.get(
            self.groupname, {}
        ).items():
            if column_name == column:
                return element
        return None

    def update_group_elements_to_columns(self):
        """Update the element to column mappings for the Group of this Entity"""
        # Only do this if we don't have any mappings of Group elements to columns
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
                # when a group is added programatically, the element to column mappings
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
            # update the element to column mappings
            for cattr in psm.class_attributes:  # noqa
                elcol_map[cattr.name] = cattr.colname
            # put it back in the dictionary
            Entity.group_elements_to_columns[self.groupname] = elcol_map

    def get_element_names(self):
        """Get the names of the elements for this entity"""
        self.update_group_elements_to_columns()
        # it is better to try to get from the extra_info
        if getattr(self, "extra_info", None) is not None:
            columns = self.extra_info.keys()
            element_names = [self.get_element_for_column(col) for col in columns]
            return element_names
        # if not, get from the group_elements_to_columns
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
            if name in self.extra_info.keys():
                nvalue = render_with_extra_info(name, getattr(self, name), extra_info)
            else:
                nvalue = getattr(self, name)
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
        if obs is None:
            obs = ""
        if extra_info is None:
            extra_info = {}
        return obs, extra_info

    # render related methods
    def description_elements(self):
        """Return a list of elements to be used in the description of the entity"""
        return ["name", "description", "desc", "title", "id"]

    def get_description(self, default=None) -> str:
        """Return a descritive name for the entity

        Uses list of description elements to get the first
        non-empty element. If no element is found, returns the default value.
        If no default is provided, returns the pom_class.
        """
        desc = None
        for element in self.description_elements():
            if hasattr(self, element):
                desc = getattr(self, element)
                break
        if desc is None or desc == "":
            if default is not None:
                desc = default
            elif hasattr(self, "pom_class") and self.pom_class is not None:
                desc = self.pom_class

        return desc if desc is not None else "Entity"

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
        show = sorted([e for e in set(els) - set(dels) if e is not None])
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

        if attr_name is not None and hasattr(self, attr_name):
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
                # if the date a just composed of digits try to format it
                if attr.isdigit():
                    attr = ftld(attr)
            if extra_info is not None and attr_name in extra_info:
                extras = extra_info.get(attr_name, {})
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
        self, self_string=None, show_contained=True,
        ident="",
        ident_inc="  ",
        show_inrels=True,
        **kwargs
    ):
        """conver the entity to a kleio string

        Args:
            self_string: the string to be used to represent the entity
            show_contained: if True, contained entities are also converted to kleio
            ident: initial identation
            ident_inc: identation increment
            show_inrels: if False, inbound relations are not shown, default is True
            kwargs: additional arguments to be passed to contained entities"""

        if self_string is None:
            s = f"{ident}{str(self)}"
        else:
            s = f"{ident}{self_string}"

        show_function = kwargs.get("show_function", False)
        contained_entities = list(
            set(self.contains)
            - set(self.rels_in or [])  # noqa: W503
            - set(self.rels_out or [])  # noqa: W503
            - set(self.attributes or [])  # noqa: W503
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
                        # if we do not show inrels, we skip the inbound relations
                        if not show_inrels:
                            continue
                    else:
                        if (not show_function) and bio_item.the_type == "function-in-act":
                            # we don't render outbound function-in-act relations
                            continue

                bio_itemk = bio_item_xi.to_kleio(
                    ident=ident + ident_inc, ident_inc=ident_inc, show_inrels=show_inrels,
                    **kwargs
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
                    ident=ident + ident_inc, ident_inc=ident_inc, show_inrels=show_inrels,
                    **kwargs
                )
                if innerk != "":
                    s = f"{s}\n{innerk}"
        return s


#  Add composite index to speed up
Index("entities_class_group", Entity.pom_class, Entity.groupname)
