"""Schemas for the Timelink API

In the FastAPi tutorial this file
is used for the pydantic models for the API,
including for the classes that are used for database access.
Another file, called models.py, is used in the tutorial
for the SQLAlchemy models.

We use a module called "models" for the SQLAlchemy models

Here we put the pydantic models that are not related to
database models like search requests and search results.

"""

# pylint: disable=too-few-public-methods

from typing import List, Optional
from datetime import datetime
from datetime import date
from pydantic import BaseModel, ConfigDict  # pylint: disable=import-error


class EntitySchema(BaseModel):
    """Pydantic Schema for Entity"""

    id: str
    pom_class: str
    inside: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    updated: Optional[datetime]
    indexed: Optional[datetime]
    contains: Optional[List["EntitySchema"]]

    model_config = ConfigDict(from_attributes=True)


class EntityBriefSchema(BaseModel):
    """Pydantic Schema for Entity brief

    No links to other entities
    """

    id: str
    pom_class: str
    inside: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    updated: Optional[datetime]
    indexed: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class RelationSchema(BaseModel):
    id: str
    origin: str
    destination: str
    the_type: str
    the_value: str
    the_date: str
    obs: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RelationOutSchema(RelationSchema):
    dest_name: Optional[str]


class RelationInSchema(RelationSchema):
    org_name: Optional[str]


class AttributeSchema(BaseModel):
    entity: str
    the_type: str
    the_value: str
    the_date: str
    obs: Optional[str]
    groupname: str = None

    model_config = ConfigDict(from_attributes=True)


class EntityAttrRelSchema(BaseModel):
    """Pydantic Schema for Entity with attributes, relation and contained entities"""

    id: str
    pom_class: str
    inside: Optional[str]
    the_order: Optional[int]
    the_level: Optional[int]
    the_line: Optional[int]
    groupname: Optional[str]
    updated: Optional[datetime]
    indexed: Optional[datetime]
    attributes: Optional[List["AttributeSchema"]]
    rels_in: Optional[List["RelationInSchema"]]
    rels_out: Optional[List["RelationOutSchema"]]
    contains: Optional[List["EntityBriefSchema"]]

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    """Search request

    Fields:
        q: search query
        after: date after which to search, possibly None
        until: date until which to search, possibly None
        skip: number of items to skip, default 0
        limit: number of items to return, default 100

    """

    q: str
    after: date | None = (
        None  # see https://docs.pydantic.dev/usage/types/#datetime-types
    )
    until: date | None = None
    skip: int | None = 0
    limit: int | None = 100


class SearchResults(BaseModel):
    """Search results

    Fields:
        results: list of search results
    """

    id: str
    the_class: str
    description: str
    start_date: date
    end_date: date


class ImportStats(BaseModel):
    """Import statistics

    Fields:
        datetime: date and time of import
        machine: machine where import was done
        database: specific database where import was done
        file: file that was imported
        import_time_seconds: time in seconds that import took
        entities_processed: number of entities processed
        entity_rate: number of entities processed per second
        person_rate: number of persons processed per second
        nerrors: number of errors
        errors: list of errors
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
