""" Module  for SQLAlchemy and Pydantic models of the Timelink Database. 

TODO: after testing for MHK schema:
    1. Implemente TemporalEntity with flexible dates
    2. Check the dataclasses new mapping https://docs.sqlalchemy.org/en/20/orm/dataclasses.html#orm-declarative-native-dataclasses
"""

from .base_class import Base  # noqa pylint: disable=unused-import
from .entity import Entity  # noqa pylint: disable=unused-import
from .attribute import Attribute  # noqa pylint: disable=unused-import
from .relation import Relation  # noqa pylint: disable=unused-import
from .act import Act  # noqa pylint: disable=unused-import
from .source import Source  # noqa pylint: disable=unused-import
from .person import Person  # noqa pylint: disable=unused-import
from .object import Object  # noqa pylint: disable=unused-import
from .pom_som_mapper import PomSomMapper, PomClassAttributes  # noqa pylint: disable=unused-import
from .base_mappings import pom_som_base_mappings  # noqa pylint: disable=unused-import
from .system import (SysPar, SysParSchema, 
                    SysLog, SysLogSchema, SysLogCreateSchema)  # noqa pylint: disable=unused-import