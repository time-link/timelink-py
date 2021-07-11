"""
Classes to generate Kleio sources.

Classes in this module allow the generation of Kleio sources.

"""
from typing import Any

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

    def __init__(self, *args, **kwargs):
        if len(args) > len(self._position):
            raise ValueError('Too many positional elements')
        self.contains = []
        n = 0
        for arg in args:
            e = self._position[n]
            setattr(self, e, KElement(e, arg))
            n = n + 1
        for (k, v) in kwargs.items():
            if k not in self._position + self._guaranteed + self._also:
                raise ValueError(f'Element not allowed: {k}')
            if not issubclass(v, KElement): # we did not get a KElement
                el = KElement(k, v)         # we make one
            else:            # we got a KElement object
                el = v
                el.name = k  # we override the element name with the arg name
            setattr(self, k, el)
        for g in self._guaranteed:
            if getattr(self, g, None) is None:
                raise TypeError(f'Element {g} in _guaranteed is missing'
                                f' or with None value')

    def include(self, group):
        if group.name not in self._part:
            raise ValueError('Group {self.name} cannot contain {group.name}')
        else:
            self.contains.append(group)

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
        more = set(self._guaranteed).union(set(self._also)).union(
            self._position).difference(out)
        print(more)
        for e in more:
            m = getattr(self, e, None)
            if m is not None:
                if not first:
                    s = s + f'/{e}={str(m)}'
                else:
                    s = s + f'{e}={str(m)}'
                    first = False
        return s

    def to_kleio(self):
        return str(self)


class KSource(KGroup):
    """ A Historical Source
    KSource(id,year,type,ref,loc=,obs=,ref=)

    Parameters
    ----------
    ref: str The call number or "cota" of the source
    loc: str Location, archive, name

    """
    _name = 'source'
    _guaranteed = ['id']
    _also = ['type', 'date', 'year', 'loc', 'ref', 'obs', 'replace']
    _position = ['id', 'year', 'type', 'ref']
    _part = ['act']
