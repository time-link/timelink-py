from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kperson import KPerson
from timelink.kleio.groups.kobject import KObject
from timelink.kleio.groups.ksource import KSource
from timelink.kleio.groups.kact import KAct


class KRelation(KGroup):
    """KRelation(type,value,destname,destination[,date=,obs=])

    A relation between historical entities.

    Relations have a type, a value, a date and a destination.
    The origin of the relation is the entity represented by the
    group that includes the relation.

    Elements:
        type: the type of the relation. A String
        value: the value of the relation. A string.
        origin: the id of the origin of the destination. A string
        destination: the id of the destination of the relation. A string.
        destname: the name of the destination of the relation. A string
        date: the date of relation. A string in Timelink format, optional.
        obs: a note on the attribute. A string optional.

    Kleio stru definition:
        part 	name=relation ;
                position=type,value,destname,destination;
                guaranteed=type,value,destname,destination ;
                also=obs,date
    """

    _name = "rel"
    _position = ["type", "value", "destname", "destination"]
    _guaranteed = ["type", "value", "destname", "destination"]
    _also = ["obs", "date", "origin"]
    _pom_class_id: str = "relation"

    def before_include(self, container_group):
        """Method called before a new krelation is included
         in a group with container_group.include(KGroup).

         It sets the origin of the relation to the id of the container group.

        Args:
            container_group (KGroup): the group that includes the relation

        Returns:
            True if the relation can be included in the group, False otherwise.

        """
        KGroup.before_include(self, container_group)
        self["origin"] = container_group.id
        return True

    def after_include(self, group):
        pass


KPerson.allow_as_part(KRelation)
KObject.allow_as_part(KRelation)
KAct.allow_as_part(KRelation)
KSource.allow_as_part(KRelation)
KGroup._rel_class = KRelation
