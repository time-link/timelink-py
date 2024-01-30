"""
Test models without requiring a db connection

"""

from timelink.mhk.models import base  # noqa
from timelink.mhk.models.entity import Entity  # noqa


def test_entity_subclasses():
    scl = list(Entity.get_subclasses())
    sc1 = len(scl)

    class SubEntity(Entity):

        __mapper_args__ = {
            "polymorphic_identity": "subentity",
            "inherit_condition": id == Entity.id,
        }
        pass

    scl2 = list(Entity.get_subclasses())
    sc2 = len(scl2)
    assert sc2 == sc1 + 1, "wrong direct subclasses of Entity"

    class SubSubEntity(SubEntity):

        __mapper_args__ = {
            "polymorphic_identity": "subsubentity",
            "inherit_condition": id == Entity.id,
        }
        pass

    scl3 = list(Entity.get_subclasses())
    sc3 = len(scl3)
    assert sc3 == sc2 + 1, "wrong recursive subclasses of Entity"
