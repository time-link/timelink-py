"""
Classes to generate Kleio sources.

Classes in this module allow the generation of Kleio sources.

"""
from os import linesep as nl
import textwrap
from typing import Any, Union, Type
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
    _source: str = None

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

    def is_empty(self):
        """True if all aspects of the element are None or empty string"""
        e = [x for x in [self.core, self.comment, self.original] if x is None or x == '']
        if len(e) == 3:
            return True
        else:
            return False

    def to_tuple(self):
        """ Return Element as a tuple (core,comment,original)"""
        return self.core, self.comment, self.original

    def to_kleio(self):
        """Return element as a kleio string: element=core#comment%original"""
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

    # TODO to_kleio_str generates the definition of a group for a kleio str file. recurse=yes
    # collects included groups and generates for those also.

    @classmethod
    def extend(cls, name: str,
               position: Union[list, None] = None,
               guaranteed: Union[list, None] = None,
               also: Union[list, None] = None,
               part: Union[list, None] = None,
               kgroup=None):
        """ Create a new class extending this one
        fonte = KGroup.extends('fonte',
                        also=['tipo',
                              'data',
                              'ano',
                              'obs',
                              'substitui'])

        """
        new_group = type(name, (cls,), {})
        new_group._name = name
        if position is not None:
            new_group._position = position
        if guaranteed is not None:
            new_group._guaranteed = guaranteed
        if also is not None:
            new_group._also = also
        if part is not None:
            new_group._part = part
        if kgroup is not None:
            new_group.kgroup = kgroup
        else:
            new_group.kgroup = name
        return new_group

    @classmethod
    def get_subclasses(cls):
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def all_subclasses(cls):
        return list(cls.get_subclasses())

    @classmethod
    def is_kgroup(cls, g):
        """True g is an instance of a subclass of KGroup"""
        return 'KGroup' in [c.__name__ for c in type(g).mro()]

    @classmethod
    def elements(cls) -> set:
        """Set of  Elements allowed in this Group"""
        return set(cls._guaranteed).union(set(cls._also)).union(
            cls._position)

    @classmethod
    def allow_as_part(cls, g: Union[str, type]):
        """ Allow g to be enclosed as part of this group.

        Arguments:
            g: the name of a group, or a subclass of KGroup.
               A string or class.
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
                raise TypeError(f'Element {g} in _guaranteed is missing or with None value')

    def include(self, group: Type['KGroup']):
        """ Include a group. `group` or its class must in _part list

        Returns self so it is possible to chain: g.include(g2).include(g3)"""
        if not self.is_kgroup(group):
            raise TypeError(f"Argument must subclasse of KGroup")
        if group._name not in self._part:
            allowed_classes = [c for c in self._part if type(c) is not str]
            super_classes = type(group).mro()
            r = list(set(super_classes).intersection(set(allowed_classes)))
            if len(r) == 0:
                raise ValueError(
                    f'Group {self._name} cannot contain {group._name}')
        self._contains.append(group)
        return self

    def includes(self):
        """Returns included groups"""
        return self._contains

    def attr(self, the_type: Union[str, tuple],
             value: Union[str, tuple],
             date: Union[str, tuple],
             obs=None):
        """ Include an KAttribute in this KGroup"""
        ka = globals()['KAttribute']
        self.include(ka(the_type, value, date=date, obs=obs))
        return self

    def rel(self, the_type: Union[str, tuple],
            value: Union[str, tuple],
            destname: Union[str, tuple],
            destination: Union[str, tuple],
            date: Union[str, tuple],
            obs: str = None):
        """ include a relation in this KGroup"""
        kr = globals()['KRelation']
        self.include(kr(the_type, value, destname, destination, date, obs))

    def to_kleio(self, indent='') -> str:
        """ Return a kleio representation of the group."""
        return self.__str__(indent=indent)

    def to_dict(self):
        """ Return group information as a dict.

        """
        kd = dict()
        for e in self.elements():
            v = getattr(self, e, None)
            if v is not None:
                kd[e] = v
        return kd

    def __str__(self, indent=""):
        sname = getattr(self, '_name', self.__class__.__name__)
        s = sname + '$'
        first = True
        out = []
        for e in self._position:
            v: KElement = getattr(self, e, None)
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
            m: KElement = getattr(self, e, None)
            if m is not None \
                and (type(m) is str and m > '' or (issubclass(type(m), KElement) and not m.is_empty())):
                if not first:
                    s = s + f'/{e}={str(m)}'
                else:
                    s = s + f'{e}={str(m)}'
                    first = False
        if len(self._contains) > 0:
            for g in self._contains:
                s = s + nl + g.__str__(indent + " ")
        return textwrap.indent(s, indent)

    def __getitem__(self, arg):
        if arg not in self.elements():
            raise ValueError("Element does not exist in group")
        return getattr(self, arg)

    def get_core(self, *args):
        """ get_core(element_name [, default])
        Returns the core value of an element
        """
        element = args[0]
        if len(args) > 1:
            default = args[1]
        else:
            default = None
        e = getattr(self, element, None)
        if e is None:
            return default
        else:
            return getattr(e, 'core', default)


class KKleio(KGroup):
    """KKleio(structure,prefix=,obs=)

    Kleio notation document. Represent a file in Kleio notation.

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
    """  KSource(id,type,loc=,ref=,date=,obs=)

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
    _part = ['act', 'attr']


KKleio.allow_as_part(KSource)


class KAct(KGroup):
    """ KAct(id,type,date[,day=,month=,year=,loc=,ref=,obs=])

    An Act is a record of an event in a specific date.

    Elements:
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
    _name = 'act'
    _guaranteed = ['id', 'type', 'date']
    _position = ['id', 'type', 'date']
    _also = ['loc', 'ref', 'obs', 'day', 'month', 'year']
    _part = ['person', 'object', 'geoentity', 'abstraction', 'ls', 'attr',
             'rel']


KSource.allow_as_part(KAct)


class KPerson(KGroup):
    """ KPerson(name,sex,id,obs=,same_as=)

    Person in a historical source

    Elements:
        name: the name of the person. A string.
        sex:  the gender of the person. A string.
        id: an unique id for this person. A string, optional.
        obs: a note on the person. A string, optional.

    Kleio str definition:

    part	name=person ;
            guaranteed=name,sex;
            also=id,obs,same_as;
            position=name,sex,id,same_as;
            arbitrary=atr,rel,ls
    """
    _name = 'person'
    _guaranteed = ['name', 'sex']
    _also = ['id', 'obs', 'same_as']
    _position = ['name', 'sex', 'id', 'same_as']
    _part = ['rel', 'attr']


KAct.allow_as_part(KPerson)


class KAttribute(KGroup):
    """ KAttribute(type,value,[date, obs=])

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
    _name = 'attr'
    _guaranteed = ['type', 'value']
    _also = ['date', 'obs']
    _position = ['type', 'value', 'date']


KPerson.allow_as_part(KAttribute)
KAct.allow_as_part(KAttribute)
KSource.allow_as_part(KAttribute)


class KLs(KAttribute):
    """Synonym for KAttribute"""

    _name = 'ls'


class KAtr(KAttribute):
    """Synonym for KAttribute"""

    _name = 'atr'


class KRelation(KGroup):
    """ KRelation(type,value,destname,destination[,date=,obs=])

    A relation between historical entities.

    Relations have a type, a value, a date and a destination.
    The origin of the relation is the entity represented by the
    group that includes the relation.

    Elements:
        type: the type of the relation. A String
        value: the value of the relation. A string.
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
    _name = 'rel'
    _position = ['type', 'value', 'destname', 'destination']
    _guaranteed = ['type', 'value', 'destname', 'destination']
    _also = ['obs', 'date']


KPerson.allow_as_part(KRelation)
KAct.allow_as_part(KRelation)
KSource.allow_as_part(KRelation)
