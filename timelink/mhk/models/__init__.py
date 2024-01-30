# flake8: noqa:F401
""" Handling of Database persistence for the Person Oriented Model (POM).

The classes on this module represent the core entities in the POM: entities,sources,
acts, people, objects, attributes and relations. SQLAlchemy is used as the
underlying ORM library.

They allow storage and query and also dynamic mapping of new types of
entities defined in ``kleio`` source files, through the PomSomMapper class.

For a detailed description of *Timelink* data models see: :doc:`som_pom_mapping`.

Also check  :class:`timelink.mhk.models.pom_som_mapper.PomSomMapper`

(c) Joaquim Carvalho 2021.
MIT License, no warranties.

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
