"""
Classes to generate Kleio sources.

Classes in this module allow the generation of Kleio sources.

"""
from typing import Any, Type

from timelink.kleio.utilities import quote_long_text


class KElement:
    """ Represents an Element in Kleio language.

    While Groups represent historical entities (people, objects, events)
    Elments encapsulate basic items of information (name, gender, date).

   The value of an Element can have three possible "aspects":

    1) "core":  the actual information for the element
    2) "original" (optional), the original wording when relevant
    3) "comment" (optional), a comment of the value.

    Example in Kleio notation:

     person$Joaquim Carvalho%Joachim Carvº#Family name added in the margin

    KElement('name','Joaquim Carvalho',original='Joachim Carvº',
            comment='Family name added in the margin')

    n = KElement('name','Joaquim Carvalho',original='Joachim Carvº',
            comment='Family name added in the margin')
    id = KElement('id','p-jrc')

    person = KPerson(id=id,name=n)

    """
    name: str
    core: Any  # must have a str representation.
    comment: str = None
    original: str = None
    _source = None

    def __init__(self, name: str, val: Any, comment=None, original=None):
        """
        Args:
            name: name of the Element. A string.
            val: the core aspect of the Element. Must have __str__
                    or a tuple (core,comment,original). If a tuple
                    optional arguments are disregarded.
            comment: Optional; The comment aspect of the Element.
            original: Optional; The original aspect of the Element.
        """

        self.name = name
        if type(val) is tuple and len(val) == 3:
            self.core = val[0]
            self.comment = val[1]
            self.original = val[2]
        else:
            self.core = val
            if comment is not None:
                self.comment = comment
            if original is not None:
                self.original = original

    def __str__(self):
        c = self.core
        cc = self.comment
        o = self.original
        if c is None:
            c = ''
        else:
            c = quote_long_text(str(c))
        if cc is None:
            cc = ''
        else:
            cc = '#' + quote_long_text(str(cc))
        if o is None:
            o = ''
        else:
            o = '%' + quote_long_text(str(o))
        return c + cc + o

    def to_kleio(self):
        return self.name + '=' + str(self)


class KGroup:
    """
    KGroup(*positional_elements ,**more_elements)

    Abstract Kleio Group.
    To define a Kleio Group extend this class and set default value for _name.
    Define allowed elements in the default values for
     _position, _guaranteed, _also (list of strings).

    Use _part to list allowed enclosed groups.

    For an example see timelink.kleio.groups.KPerson

    """

    id: str = '*id*'
    _name: str = 'kgroup'
    _position: list = []
    _guaranteed: list = []
    _also: list = []
    _part: list = []
    _contains: list = []

    @classmethod
    def allow_as_part(cls, g):
        """ Allow g to be enclosed as part of this group.

        Arguments:
            g: the name of KGroup, or a subclass of KGroup. A string or class
        """
        if g not in cls._part:
            cls._part.append(g)

        if g not in cls._part:
            cls._part.append(g)

    def __init__(self, *args, **kwargs):
        if len(args) > len(self._position):
            raise ValueError('Too many positional elements')
        self._contains = []
        n = 0
        for arg in args:
            e = self._position[n]
            setattr(self, e, KElement(e, arg))
            n = n + 1
        for (k, v) in kwargs.items():
            if k not in self._position + self._guaranteed + self._also:
                raise ValueError(f'Element not allowed: {k}')
            if not isinstance(v, KElement):  # we did not get a KElement
                el = KElement(k, v)  # we make one
            else:  # we got a KElement object
                el = v
                el.name = k  # we override the element name with the arg name
            setattr(self, k, el)
        for g in self._guaranteed:
            if getattr(self, g, None) is None:
                raise TypeError(f'Element {g} in _guaranteed is missing'
                                f' or with None value')

    # TODO test for allowed subclasses of KGroup
    # e.g. g.name in [cls.__name__ for cls in KGroup.__subclasses__()]
    # allowed_classes = [x for x in self._part if type(x) is not str]
    # super_classes = self.__mro__
    # set(super_classes).intersect(allowed_classes)
    def include(self, group):
        """ Include a group. `group` must in _part list"""
        if group._name not in self._part:
            raise ValueError(
                f'Group {self._name} cannot contain {group._name}')
        else:
            self._contains.append(group)

    def __str__(self):
        s = self._name + '$'
        first = True
        out = []
        for e in self._position:
            v = getattr(self, e, None)
            if v is not None:
                if not first:
                    s = s + '/' + str(v)
                else:
                    s = s + str(v)
                    first = False
                out.append(e)
        more = sorted(list(set(self._guaranteed).union(set(self._also)).union(
            self._position).difference(out)))
        # print(more)
        if 'obs' in more:  # we like obs elements at the end
            more.remove('obs')
            more.append('obs')
        for e in more:
            m = getattr(self, e, None)
            if m is not None:
                if not first:
                    s = s + f'/{e}={str(m)}'
                else:
                    s = s + f'{e}={str(m)}'
                    first = False
        return s

    def to_kleio(self) -> str:
        return str(self)

    def elements(self) -> set:
        """Set of  Elements allowed in this Group"""
        return set(self._guaranteed).union(set(self._also)).union(
            self._position)

    def to_dict(self):
        kd = dict()
        for e in self.elements():
            v = getattr(self, e, None)
            if v is not None:
                kd[e] = v
        return kd


class KKleio(KGroup):
    """ A Kleio notation document

    KKleio(structure,prefix=,translations=,translator=,obs=)

    Elements:
        structure: The path to a Kleio structure file (default gacto2.str)
        prefix: Prefix to be added to all ids generated from this file
        translations: number of times this file was translated
        translator: name of the translator to be used (currently not used)
        obs: observations

    """
    _name = 'kleio'
    _position = ['structure']
    _also = ['prefix', 'translations', 'translator', 'obs']
    _part = ['source', 'aregister']


class KSource(KGroup):
    """ A Historical Source
    KSource(id,type,loc=,ref=,date=,obs=)

    Elements:
        id: An unique id for this source. A string.
        type: The type of the source (e.g. baptisms, marriages); optional.

        loc: Location (name of archive, library, collection); optional.
        ref: The call reference ("cota") of the source in the location; optional.
        date: the date of the source. A string in timelink format; optional.
              1582
              1582-05-04
              1582:1609
              >1582:<1702
        year: A single year. A number. Deprecated, use date instead
        obs: Observations on the source (can be long and multiline); optional.
        replace: Id of source to be replaced. A string; optional.
                 Upon import the source with this id is removed.
                 Used when changing the id of a file.

    Kleio str definition:
        part name=historical-source;
             guaranteed=id;
             also=type,date,year,loc,ref,obs,replace;
             position=id,year,type,ref;
             part=historical-act

    """
    _name = 'source'
    _guaranteed = ['id']
    _also = ['type', 'date', 'year', 'loc', 'ref', 'replace', 'obs']
    _position = ['id']
    _part = ['act']


class KAct(KGroup):
    """ An Act in a historical Source

    An Act is a record of an event in a specific date.

    Elements:
        id: an unique id for this act. A string.
        type: type of the act (baptism, marriage, contract...). A string.
        date: the date of the act. A string in timelink format.

    Kleio str definition:

    part 	name=historical-act;
            guaranteed=id,type,date;
            position=id,type,date;
            also=loc,ref,obs,day,month,year;
            arbitrary=person,object,geoentity,abstraction,ls,atr,rel

    """
    _name = 'act'
    _guaranteed = ['id', 'tyoe', 'date']
    _position = ['id', 'type', 'date']
    _also = ['loc', 'ref', 'obs', 'day', 'month', 'year']
    _part = ['person', 'object', 'geoentity', 'abstraction', 'ls', 'atr',
             'rel']
