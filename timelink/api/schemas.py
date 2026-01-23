"""Pydantic Schemas for the Timelink API.

This module defines Pydantic models (schemas) used for data validation,
serialization, and API communication in the Timelink information system.
These models are distinct from the SQLAlchemy database models and are
used to represent data for search requests, search results, and
structured API responses.
"""

# pylint: disable=too-few-public-methods

from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict  # pylint: disable=import-error
from timelink.api.models.rentity import LinkStatus


class EntitySchema(BaseModel):
    """Pydantic Schema for a full Entity with its hierarchy.

    Attributes:
        id (str): Unique entity identifier.
        pom_class (str): The POM class name of the entity.
        inside (Optional[str]): ID of the containing entity.
        the_source (Optional[str]): Source file identifier.
        the_order (Optional[int]): Order within the source.
        the_level (Optional[int]): Hierarchy level.
        the_line (Optional[int]): Line number in source.
        groupname (Optional[str]): Kleio group name.
        updated (Optional[datetime]): Last update timestamp.
        indexed (Optional[datetime]): Last indexing timestamp.
        extra_info (Optional[dict]): Additional metadata.
        contains (Optional[List[EntitySchema]]): List of nested entities.
    """

    id: str
    pom_class: str
    inside: Optional[str]
    the_source: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    updated: Optional[datetime]
    indexed: Optional[datetime]
    extra_info: Optional[dict]
    contains: Optional[List["EntitySchema"]]

    model_config = ConfigDict(from_attributes=True)


class EntityBriefSchema(BaseModel):
    """Pydantic Schema for a simplified Entity view without hierarchical links.

    Used when only core entity information is needed without nested children.
    """

    id: str
    pom_class: str
    inside: Optional[str]
    the_source: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    extra_info: Optional[dict]
    updated: Optional[datetime]
    indexed: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RelationSchema(BaseModel):
    """Pydantic Schema for an Entity Relationship.

    Represents a directed relationship between two entities.
    """
    id: str
    origin: str
    destination: str
    the_type: str
    the_value: str
    the_date: str
    obs: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RelationOutSchema(RelationSchema):
    """Pydantic Schema for an outgoing relationship including the destination name."""
    dest_name: Optional[str]


class RelationInSchema(RelationSchema):
    """Pydantic Schema for an incoming relationship including the origin name."""
    org_name: Optional[str]


class AttributeSchema(BaseModel):
    """Pydantic Schema for an Entity Attribute.

    Represents a specific characteristic or property assigned to an entity.
    """
    entity: str
    the_type: str
    the_value: str
    the_date: str
    obs: Optional[str]
    groupname: str = None

    model_config = ConfigDict(from_attributes=True)


class EntityAttrRelSchema(BaseModel):
    """Pydantic Schema for an Entity with its attributes, relations, and hierarchy.

    This is a comprehensive schema used to represent an entity along with all
    its associated data and nested structure.
    """

    id: str
    pom_class: str
    inside: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    the_source: Optional[str]
    updated: Optional[datetime]
    indexed: Optional[datetime]
    extra_info: Optional[dict]
    attributes: Optional[List["AttributeSchema"]]
    rels_in: Optional[List["RelationInSchema"]]
    rels_out: Optional[List["RelationOutSchema"]]
    contains: Optional[List["EntityAttrRelSchema"]]
    links: Optional[List["LinkSchema"]]

    model_config = ConfigDict(from_attributes=True)


class RealEntitySchema(BaseModel):
    """Pydantic Schema for a RealEntity (reconciled entity) brief view.

    Represents a "real world" entity that links multiple historical occurrences.
    """

    id: str
    user: str
    description: Optional[str]
    status: LinkStatus
    obs: Optional[str]
    links: Optional[List["LinkSchema"]]

    model_config = ConfigDict(from_attributes=True)


class RealEntityAttrRelSchema(BaseModel):
    """Pydantic Schema for a RealEntity with all its associated data.

    Includes aggregated attributes and relations from linked historical entities.
    """

    id: str
    user: str
    description: Optional[str]
    status: LinkStatus
    obs: Optional[str]
    attributes: Optional[List["AttributeSchema"]]
    rels_in: Optional[List["RelationInSchema"]]
    rels_out: Optional[List["RelationOutSchema"]]
    contains: Optional[List["EntityBriefSchema"]]
    links: Optional[List["LinkSchema"]]

    model_config = ConfigDict(from_attributes=True)


class LinkSchema(BaseModel):
    """Pydantic Schema for identification links between entities."""

    id: int
    rid: str
    entity: str
    user: str
    rule: str
    source: str
    status: LinkStatus
    aregister: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    """Pydantic Schema for a search query request.

    Attributes:
        q (str): The search query string.
        after (date, optional): Only return results after this date.
        until (date, optional): Only return results until this date.
        skip (int, optional): Number of items to skip for pagination. Defaults to 0.
        limit (int, optional): Maximum number of items to return. Defaults to 100.
    """

    q: str
    after: date | None = None
    until: date | None = None
    skip: int | None = 0
    limit: int | None = 100


class SearchResults(BaseModel):
    """Pydantic Schema for a single search result entry."""

    id: str
    the_class: str
    description: str
    start_date: date
    end_date: date


class ImportStats(BaseModel):
    """Pydantic Schema for data import statistics.

    Attributes:
        datetime (date): Date of the import.
        machine (str): Hostname of the machine performing the import.
        database (str): Name of the target database.
        file (str): Path of the file being imported.
        import_time_seconds (float): Total duration of the import process.
        entities_processed (int): Total number of entities handled.
        entity_rate (float): Entities processed per second.
        person_rate (float): Persons processed per second.
        nerrors (int): Total number of errors encountered.
        errors (List[str]): List of specific error messages.
    """

    datetime: date
    machine: str
    database: str
    file: str
    import_time_seconds: float
    entities_processed: int
    entity_rate: float
    person_rate: float
    nerrors: int
    errors: List[str]
