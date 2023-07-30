from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kperson import KPerson
from timelink.kleio.groups.kobject import KObject
from timelink.kleio.groups.ksource import KSource
from timelink.kleio.groups.kact import KAct
from timelink.kleio.groups.kelement import KEntityInAttribute


class KAttribute(KGroup):
    """KAttribute(type,value,[date, obs=])

    Time varying attribute of a person, object, or other

    Attributes represent time-varying information about historical entities.
    Each attribute has a type ('address','profession', 'age'), a value and
    a date associated with the attribute.

    Elements:
        type: the type of the attribute. A String
        value: the value of the attribute. A string.
        date: the date of attribute. A string in Timelink format, optional.
        obs: a note on the attribute. A string optional.

     Kleio str definition :
        part	name=attribute ;
                guaranteed=type,value ;
                also=obs,date ;
                position=type,value,date

    """

    _name = "attr"
    _guaranteed = ["type", "value"]
    _also = ["date", "obs", "entity"]  # entity is automatically set
    _position = ["type", "value", "date"]
    _pom_class_id: str = "attribute"

    def before_include(self, container_group):
        """Method called before a new group is included in this one
        through KGroup.include(KGroup).
        """
        KGroup.before_include(self, container_group)
        self["entity"] = KEntityInAttribute("entity", container_group.id.core)
        return True

    def after_include(self, group):
        pass


KPerson.allow_as_part(KAttribute)
KObject.allow_as_part(KAttribute)
KAct.allow_as_part(KAttribute)
KSource.allow_as_part(KAttribute)
KGroup._attr_class = KAttribute
