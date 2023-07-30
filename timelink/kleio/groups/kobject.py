from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kact import KAct


class KObject(KGroup):
    """KObject(name,type,id=,obs=,same_as=,xsame_as=)

    An object in a historical source.
    Object groups represent physical entities like
    houses, pieces of land, movable objects

    Elements:
        name: the name of the object. A string.
        type:  the . A string.
        id: an unique id for this person. A string, optional.
        obs: a note on the person. A string, optional.
        same_as: id of another instance of this object in the same file.
        xsame_as: id of another instance of this object in another file.

    Kleio str definition:

        part name=object;
             guaranteed=name;
             position=name,type;
             also=obs,id,same_as,xsame_as;
             arbitrary=atr,ls,rel
    """

    _name = "object"
    _guaranteed = ["name"]
    _also = ["id", "obs", "same_as"]
    _position = ["name", "sex", "id", "same_as", "xsame_as"]
    _part = ["rel", "attr"]
    _pom_class_id: str = "object"


KAct.allow_as_part(KObject)
