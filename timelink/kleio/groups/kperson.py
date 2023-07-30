from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kact import KAct


class KPerson(KGroup):
    """KPerson(name,sex,id,obs=,same_as=,xsame_as=)

    Person in a historical source

    Elements:
        name: the name of the person. A string.
        sex:  the gender of the person. A string.
        id: an unique id for this person. A string, optional.
        obs: a note on the person. A string, optional.
        same_as: id of another instance of this person in the same file.
        xsame_as: id of another instance of this person in another file.

    Kleio str definition:

    part	name=person ;
            guaranteed=name,sex;
            also=id,obs,same_as;
            position=name,sex,id,same_as;
            arbitrary=atr,rel,ls
    """

    _name = "person"
    _guaranteed = ["name", "sex"]
    _also = ["id", "obs", "same_as"]
    _position = ["name", "sex", "id", "same_as", "xsame_as"]
    _part = ["rel", "attr"]
    _pom_class_id: str = "person"


KAct.allow_as_part(KPerson)
