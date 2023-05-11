"""Schemas for the Timelink API

In the FastAPi tutorial this file
is used for the pydantic models for the API,
including for the classes that are used for database access.
Another file, called models.py, is used in the tutorial 
for the SQLAlchemy models.

We use a module called "models" for the SQLAlchemy models and
pydantic models for the API, and we put them together in each file
of the "models" module.

Here we put the pydantic models that are not related to database models
like search requests and search results.

"""

from typing import List
from enum import Enum
from datetime import date
from pydantic import BaseModel # pylint: disable=import-error

class EntityBase(BaseModel):
    name: str

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
    after: date | None = None  # see https://docs.pydantic.dev/usage/types/#datetime-types
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
        file: file that was imported
        import_time_seconds: time in seconds that import took
        entities_processed: number of entities processed
        entity_rate: number of entities processed per second
        person_rate: number of persons processed per second
    """
    
    datetime: date
    machine: str
    file: str
    import_time_seconds: float
    entities_processed: int
    entity_rate: float
    person_rate: float