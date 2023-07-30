# Import all the models, so that Base has them before being
# imported by Alembic
# pylint: disable=import-error

from timelink.mhk.models.base_class import Base  # noqa
from timelink.mhk.models.entity import Entity  # noqa
from timelink.mhk.models.pom_som_mapper import PomSomMapper, PomClassAttributes  # noqa
from timelink.mhk.models.attribute import Attribute  # noqa
from timelink.mhk.models.relation import Relation  # noqa
from timelink.mhk.models.person import Person  # noqa
from timelink.mhk.models.object import Object  # noqa
from timelink.mhk.models.act import Act  # noqa
from timelink.mhk.models.source import Source  # noqa
