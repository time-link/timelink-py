from timelink.kleio.groups.kobject import KObject
from timelink.kleio.groups.kact import KAct


class KAbstraction(KObject):
    """A synonym for object, used in non physical entities such as
    institutions.

    """

    pass


KAct.allow_as_part(KAbstraction)
