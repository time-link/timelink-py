from timelink.kleio.groups.kobject import KObject
from timelink.kleio.groups.kact import KAct


class KAbstraction(KObject):
    """KAbstraction(name,type,id=,obs=,same_as=,xsame_as=)
    A synonym for object, used in non physical entities such as
    institutions.
    """

    pass


KAct.allow_as_part(KAbstraction)
