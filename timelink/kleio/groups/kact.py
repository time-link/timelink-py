from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.ksource import KSource


class KAct(KGroup):
    """KAct(id,type,date[,day=,month=,year=,loc=,ref=,obs=])

    An Act is a record of an event in a specific date.

    Fields:

        id: an unique id for this act. A string.
        type: type of the act (baptism, marriage, contract...). A string.
        date: the date of the act. A string in timelink format.
        day,month,year: the date expressed in individual values
        loc: location of the act in the archive (if different from source)
        ref: call number, or page number in source.

    Kleio str definition:

    part 	name=historical-act;
            guaranteed=id,type,date;
            position=id,type,date;
            also=loc,ref,obs,day,month,year;
            arbitrary=person,object,geoentity,abstraction,ls,atr,rel

    """

    _name = "act"
    _guaranteed = ["id", "type", "date"]
    _position = ["id", "type", "date"]
    _also = ["loc", "ref", "obs", "day", "month", "year"]
    _part = ["person", "object", "geoentity", "abstraction", "ls", "attr", "rel"]
    _pom_class_id: str = "act"


KSource.allow_as_part(KAct)
