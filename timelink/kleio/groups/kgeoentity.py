from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kact import KAct


class KGeoentity(KGroup):
    """KGeoentity(name,type,id=,obs=,same_as=,xsame_as=)

    A geographic entity. Flags an Entity as a geographic entity.
    No specific fields are defined for this class.

    Elements:
        name: the name of the object. A string.
        type:  the . A string.
        id: an unique id for this person. A string, optional.
        obs: a note on the person. A string, optional.
        same_as: id of another instance of this object in the same file.
        xsame_as: id of another instance of this object in another file.

    Kleio str definition:

            part name=geoentity;
                position=name; guaranteed=name;
                also=type,id,obs,same_as,xsame_as;
                part=ls,atr,rel

    """

    _name = "geoentity"
    _guaranteed = ["name"]
    _also = ["id", "type", "obs", "same_as", "xsame_as"]
    _position = ["name", "id"]
    _part = ["rel", "attr"]
    _pom_class_id: str = "geoentity"


KAct.allow_as_part(KGeoentity)
