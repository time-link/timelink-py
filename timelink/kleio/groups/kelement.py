from typing import Any

from box import Box

from timelink.kleio.utilities import quote_long_text


class KElement:
    """ Represents an Element in Kleio language.

    While *Groups* represent historical entities (people, objects, events)
    *Elements* encapsulate basic items of information (name, gender, date).

   The value of an Element can have three possible "aspects":

    1) "core":  the actual information for the element
    2) "original" (optional), the original wording when relevant
    3) "comment" (optional), a comment of the value.

    Example in Kleio notation::

        person$Joaquim Carvalho%Joachim Carvº#Family name added in the margin

    Can be generated by ::

        n = KElement('name','Joaquim Carvalho',original='Joachim Carvº',
                comment='Family name added in the margin')
        id = KElement('id','p-jrc')
        person = KPerson(id=id,name=n)

    TODO: does not deal with multiple values in elements.
    Check KElement in MHK where core, comment and original are Vectors
    better to create a KAspect class.

    """
    name: str = None
    core: Any  # must have a str representation.
    comment: str = None
    original: str = None
    _element_class = None

    @property
    def element_class(self):
        """ This return _element_class if existing or name if not."""
        if self._element_class is not None:
            return self._element_class
        else:
            return self.__class__.name

    @element_class.setter
    def element_class(self, value):
        pass

    def __init__(self, name: str = None, core: Any = None, comment=None,
                 original=None,
                 element_class=None):
        """
        Args:
            name: name of the Element. If None then self._name is used.
            core: the core aspect of the Element. Must have __str__
                    or a tuple (core,comment,original). If a tuple
                    optional arguments are disregarded.
            comment: Optional; The comment aspect of the Element.
            original: Optional; The original aspect of the Element.
            element_class: Optional; in groups from kleio translations
                this is set by the translator from the the source=parameter.
                of the str file. If absent it is set here
                equal to the name of the element.
        """
        if name is not None:
            self.name = name

        if type(core) is tuple and len(core) == 3:
            self.core = core[0]
            self.comment = core[1]
            self.original = core[2]
        else:
            self.core = core
            if comment is not None:
                self.comment = comment
            if original is not None:
                self.original = original
        if element_class is not None:
            kclass = self.__class__.get_class_for(element_class)
            if kclass is not None:
                self.__class__.extend(name)

    def __str__(self):
        return self.core

    def __int__(self):
        return int(str(self))

    @classmethod
    def extend(cls, name: str):
        """
        Creates a new KElement class that extends this one.
        This allows creating new KElement
        names for different languages and keep the behaviour of
        a specific element type (e.g. mapping "data" elements
        behave like "date" elements).

        When an element of a group is set with an atomic value
        or a tuple, a new KElement of the class with the same
        name of the element in the group is used to store the
        group.

        :param name:
        :return:
        """
        new_kelement = type(name, (cls,), {})
        new_kelement.name = name
        return new_kelement

    @classmethod
    def get_subclasses(cls):
        """ Generator for subclasses of this KElement"""
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def all_subclasses(cls):
        """ List of all the subclasses of this KElement"""
        return list(cls.get_subclasses())

    @classmethod
    def get_class_for(cls, name: str):
        """
        Search in KElement subclasses and return the one
        with the same element name as the argument.

        if more than one apply return the more specialized (longer __mro__)

        If not found return None

        :param name: name of an element
        :return: KElement or a subclass
        """
        search_list = sorted([(a, len(a.__mro__))
                              for a in cls.all_subclasses()],
                             key=lambda mro: -mro[1])
        for eclass, _mro in search_list:
            if eclass.name == name:
                return eclass
        return None

    @classmethod
    def inherits_from(cls):
        return [ke for ke in cls.__mro__ if ke is not object
                and ke is not None]

    @classmethod
    def get_classes_for(cls, name: str):
        """ Search in Element subclass and return all that
        have the same element name as the argument

        see KElement.get_class_for(name) for getting the more specialized"""
        return [sc for sc in KElement.all_subclasses() if sc.name == name]

    def inherited_names(self):
        """ Return the list of names in the KElement subclasses
        this element inherits from including its own"""
        return [ke.name for ke in self.__class__.__mro__ if ke is not object
                and ke.name is not None]

    def extends(self, name: str):
        """True if name is in the the classes this element inherits from"""
        return name in self.inherited_names()

    def is_empty(self):
        """True if all aspects of the element are None or empty string"""
        e = [x for x in [self.core, self.comment, self.original] if
             x is None or x == '']
        if len(e) == 3:
            return True
        else:
            return False

    def to_tuple(self):
        """ Return Element as a tuple (core,comment,original)"""
        return self.core, self.comment, self.original

    def to_kleio(self, name=True, force_show=False):
        """
        Return element as a kleio string: element=core#comment%original
        To avoid rendering the element name set name=False
        :param name: if True(default) prefix value with self.name=
        :return: a valid Kleio representation of this element value
        """
        if self.extends('invisible_') and force_show is False:
            return ''
        if self.is_empty():
            return ''
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
        kleio = c + cc + o
        if name:
            kleio = f"{self.name}={kleio}"
        return kleio

    def to_dict(self, name=False):
        """ Return Element as a dict {core:_, comment:_, original:_}
        add name=True to add name to dictionary:
        {name:_, core:_, comment:_, original:_}"""
        if name:
            return {'name': self.name,
                    'core': self.core, 'comment': self.comment,
                    'original': self.original}
        else:
            return {'core': self.core, 'comment': self.comment,
                    'original': self.original}

    def to_dots(self):
        return Box(self.to_dict())


KleioNoShow = KElement.extend('invisible_')


# Default KElement classes.
# element name=id; identification=yes
# element name=type
# element name=loc
# element name=obs
# element name=ref
# element name=value
# element name=origin
# element name=destination
# element name=entity
# element name=same_as
# element name=xsame_as
# element name=name
# element name=sex
# element name=destname
# element name=destination
# element name=summary;
# element name=description;
# element name=replace;

# use this for mixins to mark this should show in Kleio
# still can override with KElement.to_kleio(force_show=True


class KDate(KElement):
    name = 'date'

    def __init__(self, date: Any = None, core=None, comment=None,
                 original=None,
                 element_class=None):
        if core is not None:
            date = core  # to allow core setting in generic code
        super().__init__(self.name, date, comment, original, element_class)


class KDay(KElement):
    name = 'day'

    def __init__(self, day: Any = None, core=None, comment=None,
                 original=None,
                 element_class=None):
        if core is not None:
            day = core  # to allow core setting in generic code
        super().__init__(self.name, day, comment, original, element_class)
        if type(self.core) is str:
            self.core = int(self.core)
        if self.core != 0 and (self.core < 1 or self.core > 31):
            raise ValueError("Day value must be between 1 and 31")


class KMonth(KElement):
    name = 'month'

    def __init__(self, month: Any = None, core=None, comment=None,
                 original=None,
                 element_class=None):
        if core is not None:
            month = core  # to allow core
        super().__init__(self.name, month, comment, original, element_class)

        self.core = int(self.core)

        if type(self.core) is str:
            self.core = int(self.core)
        if self.core != 0 and (self.core < 1 or self.core > 12):
            raise ValueError("Month value must be between 1 and 12")


class KYear(KElement):
    """
    Represents a year.

    To have value checking do KYear.set_limits((lower,upper))

    """
    name = 'year'

    def __init__(self, year: Any = None, core=None, comment=None,
                 original=None):
        if core is not None:
            year = core

        super().__init__(self.name, year, comment, original)

        self.core = int(self.core)


class KType(KElement):
    """
    Represents a type of object or abstraction
    """
    name = 'type'


class KValue(KElement):
    """
    Represents a general purpose value
    """
    name = 'value'


class KId(KElement):
    """
    Represents an unique id for a group.

    """
    name = 'id'


class KEntityInAttribute(KId, KleioNoShow):
    name = 'entity'


class KOriginInRel(KId, KleioNoShow):
    name = 'origin'


class KReplace(KElement):
    """
    Represents the id of a group to be replaced.

    Example:

        source$new-id/replace=old-id
    """
    name = 'replace'


class KSameAs(KElement):
    """
    Represents the id of a group that describes the
    same real world entity has the one with this element.

    Used in the same file. Translators should check if
    the id corresponds to a group in the same file and
    file an error otherwise

    Example:
        person$Bob Dylan/id=bob-dylan
        .....
        person$Robert Allan Zimmerman/sameas=bob-dylan
    """
    name = 'same_as'


class KXSameAs(KElement):
    """
    Same meaning as KSameAs used when id is not
    in the file.

    The difference between KSameAs and KXSameAs is
    just for error checking during translation.
    Translators will raise error if a KSameAs id
    is not found in the same file, but only a warning
    for KXSameAs.

    """
    name = 'xsame_as'


class KName(KElement):
    """
    Name of person
    """
    name = 'name'


class KSex(KElement):
    """
    male / female ...
    """
    name = 'sex'


class KDescription(KElement):
    """
    Similar to name, for objects
    """
    name = 'description'


class KObs(KElement):
    """
    Element for "obs" normally observations or notes
    """
    name = 'obs'


class KStructure(KElement):
    """
    Element for structure name in sources
    """
    name = 'structure'


class KLoc(KElement):
    """
    Element for location (in a document, e.g. page)  in some groups
    """
    name = 'loc'


class KRef(KElement):
    """
    Element for reference number (e.g. a call number in an archive)
    """
    name = 'ref'


class KDestName(KElement):
    """
    Element for destination names in relations
    """
    name = 'destname'


class KDestId(KElement):
    """
    Element for destination id in relations
    """
    name = 'destination'


class KSummary(KElement):
    """
    Element for summaries (long texts)
    """
    name = 'summary'


class KReplaceSourceId(KElement):
    """
    Element for id of source being replaced in source groups
    """
    name = 'replace'


# Automatic elements, generated during the translation process


class KKleiofile(KElement):
    """
    Element for the name of the file from which the source was imported
    """
    name = 'kleiofile'


class KGroupName(KElement):
    """
    Element for groupname of a group
    """
    name = 'groupname'


class KClass(KElement):
    """
    Element for the class of a group
    """
    name = 'class'


class KLevel(KElement):
    """
    Element for nesting level in imported groups
    """
    name = 'level'


class KLine(KElement):
    """
    Element for line number in imported groups
    """
    name = 'line'


class KOrder(KElement):
    """
    Element for group order in imported groups
    """
    name = 'order'


class KInside(KElement):
    """
    Element for id of the enclosing group
    """
    name = 'inside'


class KUndef(KElement):
    """
    Element of undefined class (generated by the kleio translator)

    This is generated when the translator finds an element for which
    the is no mapping POM_SOM in any class. An example if the elements
    for day,month,year that are used for input but are stored as a single
    value YYYYMMDD and so are not present in the mapping information for
    database storage.
    """
    name = 'undef'