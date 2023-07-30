from timelink.kleio.groups.kgroup import KGroup
from timelink.kleio.groups.kkleio import KKleio


class KSource(KGroup):
    """Represents an Historical Source. Sources contain :class:`KAct` and
    may contain :class:`KAttribute`.

    Elements

    id
        An unique id for this source.
    type
        The type of the source (e.g. baptisms, marriages); optional.
    loc
        Location (name of archive, library, collection); optional.
    ref
        The call reference ("cota") of the source in the location; optional.
    date
        The date of the source. A string in timelink format; optional.

          - 1582
          - 1582-05-04
          - 1582:1609
          - >1582:<1702
    year
        A single year. A number. Deprecated, use date instead
    obs
        Observations on the source (can be long and multiline); optional.
    replace
        Id of source to be replaced. A string; optional.
        The source with this id is removed before importing this one.
        Used when changing the id of a file, old id should go here.

    Kleio str definition::

        part name=historical-source;
             guaranteed=id;
             also=type,date,year,loc,ref,obs,replace;
             position=id,year,type,ref;
             part=historical-act


    """

    _name = "source"
    _guaranteed = ["id"]
    _also = ["type", "date", "year", "loc", "ref", "replace", "obs"]
    _position = ["id"]
    _part = ["act", "attr"]
    _pom_class_id: str = "source"


KKleio.allow_as_part(KSource)
