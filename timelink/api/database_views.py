"""Database Views Mixin for Timelink.

This module provides the DatabaseViewsMixin class, which contains methods for
creating and managing SQL views in the Timelink database. These views join
core tables to provide simplified access to complex relational data, such
as attributes with entity names, functions in acts, and named entity relationships.
"""
from sqlalchemy import (
    MetaData,
    select,
    union,
)
from sqlalchemy.orm import aliased

from timelink.api.models import (
    Attribute,
    Entity,
    Person,
)
from timelink.api.models.act import Act
from timelink.api.models.geoentity import Geoentity
from timelink.api.models.object import Object
from timelink.mhk.models.relation import Relation

from . import views


class DatabaseViewsMixin:
    """Methods for creating and managing database views.

    This mixin handles the creation, deletion, and updating of standard SQL views
    used within the Timelink information system.
    """

    def _create_nattributes_view(self):
        """Create the 'nattributes' view for named entity attributes.

        This view joins the 'persons' table with the 'attributes' table to provide
        attribute values alongside person names and sex information.

        Returns:
            Table: A SQLAlchemy view object representing the nattributes view.

        Note:
            The 'id' column contains the person's ID, not the attribute's ID.

        Example SQL::

            CREATE VIEW nattributes AS
                SELECT p.id        AS id,
                    p.name      AS name,
                    p.sex       AS sex,
                    a.id        AS attr_id,
                    a.the_type  AS the_type,
                    a.the_value AS the_value,
                    a.the_date  AS the_date,
                    p.obs       AS pobs,
                    a.obs       AS aobs
                FROM attributes a, persons p
                WHERE (a.entity = p.id)
        """
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("pattributes")
        person = Person.__table__
        attribute = Attribute.__table__

        attr = views.view(
            "nattributes",
            metadata,
            select(
                person.c.id.label("id"),
                person.c.name.label("name"),
                person.c.sex.label("sex"),
                attribute.c.id.label("attr_id"),
                attribute.c.the_type.label("the_type"),
                attribute.c.the_value.label("the_value"),
                attribute.c.the_date.label("the_date"),
                person.c.obs.label("pobs"),
                attribute.c.obs.label("aobs"),
            ).select_from(person.join(attribute, person.c.id == attribute.c.entity)),
        )
        return attr

    def _create_eattribute_view(self):
        """Create the 'eattributes' view for entity attributes with positional info.

        This view joins the 'entities' and 'attributes' tables to provide attribute
        values along with "positional" metadata from the entities table, such as
        line number, level, order in the source file, groupname, and timestamps.

        Returns:
            Table: A SQLAlchemy view object representing the eattributes view.
        """

        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("eattributes")

        entity = Entity.__table__
        attribute = Attribute.__table__
        attr_entity = aliased(Entity.__table__)
        attr = views.view(
            "eattributes",
            metadata,
            select(
                entity.c.id.label("id"),
                entity.c.the_line.label("e_the_line"),
                entity.c.the_level.label("e_the_level"),
                entity.c.the_order.label("e_the_order"),
                entity.c.groupname.label("e_groupname"),
                entity.c.updated.label("updated"),
                entity.c.indexed.label("indexed"),
                entity.c.extra_info.label("e_extra_info"),
                attribute.c.id.label("attr_id"),
                attribute.c.entity.label("entity"),
                attribute.c.the_type.label("the_type"),
                attribute.c.the_value.label("the_value"),
                attribute.c.the_date.label("the_date"),
                attribute.c.obs.label("aobs"),
                attr_entity.c.the_line.label("a_the_line"),
                attr_entity.c.the_level.label("a_the_level"),
                attr_entity.c.the_order.label("a_the_order"),
                attr_entity.c.groupname.label("a_groupname"),
                attr_entity.c.extra_info.label("a_extra_info"),
            ).select_from(
                entity.join(attribute, entity.c.id == attribute.c.entity).join(
                    attr_entity, attribute.c.id == attr_entity.c.id
                )
            ),
        )
        return attr

    def _create_named_entity_view(self):
        """Create the 'named_entities' view for entities with names.

        This view creates a unified interface for persons, objects, and geoentities
        by unioning their IDs and names and joining with the core entities table.

        Returns:
            Table: A SQLAlchemy view object representing the named_entities view.
        """
        metadata: MetaData = self.metadata

        # We should have a class "named_entity" to mixin
        #  and detect dynamically.

        person = Person.__table__
        object = Object.__table__
        geoentity = Geoentity.__table__
        entity = Entity.__table__
        sel1 = select(
            person.c.id.label("id"),
            person.c.name.label("name"),
        )
        sel2 = select(
            object.c.id.label("id"),
            object.c.name.label("name"),
        )
        sel3 = select(
            geoentity.c.id.label("id"),
            geoentity.c.name.label("name"),
        )
        union_all = union(sel1, sel2, sel3).subquery()

        named_entities = views.view(
            "named_entities",
            metadata,
            select(
                entity.c.id.label("id"),
                entity.c.groupname.label("groupname"),
                entity.c["class"].label("pom_class"),
                entity.c.the_line.label("the_line"),
                entity.c.the_level.label("the_level"),
                entity.c.the_order.label("the_order"),
                entity.c.updated.label("updated"),
                entity.c.indexed.label("indexed"),
                entity.c.extra_info.label("extra_info"),
                union_all.c.name.label("name"),
            ).select_from(entity.join(union_all, entity.c.id == union_all.c.id)),
        )
        return named_entities

    def _create_nfunction_view(self):
        """Create the 'nfunctions' view linking people to acts through functions.

        This view joins the named_entities view with relations and acts tables
        to show which persons performed which functions in which acts.

        Returns:
            Table: A SQLAlchemy view object representing the nfunctions view.
        """
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("nfuncs")

        named_entity = self.views["named_entities"]
        act = (
            Act.__table__
        )  # this can be replaced by aliased(Act) and get the full act with entity info
        relation = Relation.__table__
        nfuncs = views.view(
            "nfunctions",
            metadata,
            select(
                named_entity.c.id.label("id"),
                named_entity.c.name.label("name"),
                named_entity.c.groupname.label("groupname"),
                named_entity.c.pom_class.label("pom_class"),
                named_entity.c.the_line.label("the_line"),
                named_entity.c.the_level.label("the_level"),
                named_entity.c.the_order.label("the_order"),
                named_entity.c.updated.label("updated"),
                named_entity.c.indexed.label("indexed"),
                named_entity.c.extra_info.label("extra_info"),
                relation.c.the_value.label("func"),
                act.c.id.label("id_act"),
                act.c.the_type.label("act_type"),
                act.c.the_date.label("act_date"),
                act.c.obs.label("act_obs"),
            )
            .select_from(
                named_entity.join(
                    relation, named_entity.c.id == relation.c.origin
                ).join(act, relation.c.destination == act.c.id)
            )
            .where(relation.c.the_type == "function-in-act"),
        )
        return nfuncs

    def _create_nrelations_view(self):
        """Create the 'nrelations' view linking relations with named entities.

        This view provides easy access to the names of entities involved in relationships
        by joining the relations table with the named_entities view for both origin
        and destination entities.

        Returns:
            Table: A SQLAlchemy view object representing the nrelations view.

        Note:
            Inspired by the MHK 'nrels' view.

        Example SQL::

            CREATE VIEW nrels AS
                SELECT
                    relations.id,
                    p1.id   AS ida,
                    p1.name AS namea,
                    p1.sex  as sexa,
                    p2.id   AS idb,
                    p2.name AS nameb,
                    p2.sex  AS sexb,
                    relations.the_type,
                    relations.the_value,
                    relations.the_date,
                    relations.obs
                FROM relations, persons p1, persons p2
                WHERE relations.origin = p1.id
                    AND relations.destination = p2.id
                    AND relations.the_type <> 'Identification';
        """
        metadata: MetaData = self.metadata
        # texists = inspect(eng).has_table("nrelations")
        origin = self.views["named_entities"]
        destination = aliased(origin)
        relation = self.get_table("relations")
        nrelations = views.view(
            "nrelations",
            metadata,
            select(
                relation.c.id.label("relation_id"),
                origin.c.id.label("origin_id"),
                origin.c.name.label("origin_name"),
                destination.c.id.label("destination_id"),
                destination.c.name.label("destination_name"),
                relation.c.the_type.label("relation_type"),
                relation.c.the_value.label("relation_value"),
                relation.c.the_date.label("relation_date"),
            ).select_from(
                relation.join(origin, relation.c.origin == origin.c.id).join(
                    destination, relation.c.destination == destination.c.id
                )
            ),
        )
        return nrelations
