import json
import textwrap
import warnings
from os import linesep as nl
from typing import Type, List, Union, Tuple, Dict

from box import Box

from timelink.kleio.groups.kelement import KElement


class KGroup:
    """
    KGroup(*positional_elements ,**more_elements)

    Abstract Kleio Group.

    To define a Kleio Group extend this class and set default value for _name,
    or use extend(name,position, guaranteed, also).

    Define allowed elements in the default values for _position, _guaranteed,
    _also (list of strings) or call allowed_as_element .

    Use _part to list allowed enclosed groups, or call allow_as_part

    For an example see timelink.kleio.groups.KPerson

    """

    # Class scoped list of reserved element names for system use
    _builtin_elements = [
        "line",
        "level",
        "order",
        "inside",
        "groupname",
        "pom_class_id",
        "id",
    ]

    id = None
    _name: str = "kgroup"
    _position: list = []  # list of positional elements
    _guaranteed: list = []  # list of required elements
    _also: list = []  # list of optional elements
    _part: list = []  # allowed sub groups

    _extends: Type["KGroup"]  # name of group this is based on
    _pom_class_id: str = "entity"  # Id of PomSom mapper for this group
    _element_check = True  # if true validates element assignment
    _elementsd: Type[Dict[str, KElement]]  # Current elements
    _inside: Type["KGroup"]  # group that includes this

    # The following fields are generated during the translation process.
    # If the Kleio groups are generated programatically (for instance when
    # importing from csv files or from databases) then the cls.include method
    # will update these values
    _line: int  # line in the source file
    _level: int  # nesting always +1  than enclosing group
    _order: int  # sequential number of this group in the original source
    # class scoped counters to ensure proper numbering across different groups
    _global_sequence: int = 1  # global sequence count
    _global_line: int = 1  # global line count

    # we need the classes for attributes and relations, used by the
    # attr and rel methods. Since those class are subclasses of this one
    # they need to set this latter. Also allows for differet classes to
    # be used by attr and rel if necessary
    _attr_class = None  # class used by the attr method (set by KAttribute)
    _rel_class = None  # class used by the rel method (set by KRelation)

    # TODO to_kleio_str generates the definition of a group
    #       for a kleio str file. recurse=yes
    #       collects included groups and generates for those also.

    @property
    def kname(self):
        """The kleio name of this group, used in the to_kleio() method"""
        return self.unpack_from_kelement(self._name)

    @kname.setter
    def kname(self, value):
        self._name = self.pack_as_kelement("kname", value, element_class="name")

    @property
    def inside(self):
        return self._inside

    def get_container_id(self):
        if self._inside is None:
            gid = None
        elif KGroup.is_kgroup(self._inside):
            gid = self.unpack_from_kelement(self.inside.id)
        return gid

    @inside.setter
    def inside(self, value):
        if KGroup.is_kgroup(value):
            self._inside = value
        else:
            self._inside = KGroup(id=str(value), element_check=False)

    @property
    def line(self):
        return self.unpack_from_kelement(self._line)

    @line.setter
    def line(self, value):
        self._line = self.pack_as_kelement("line", value)

    @property
    def level(self):
        return self.unpack_from_kelement(self._level)

    @level.setter
    def level(self, value):
        self._level = self.pack_as_kelement("level", value)

    @property
    def order(self):
        return self.unpack_from_kelement(self._order)

    @order.setter
    def order(self, value):
        self._order = self.pack_as_kelement("order", value)

    @property
    def pom_class_id(self):
        return self.unpack_from_kelement(self._pom_class_id)

    @pom_class_id.setter
    def pom_class_id(self, pcid):
        self._pom_class_id = self.pack_as_kelement("pom_class_id", pcid)

    @classmethod
    def extend(
        cls,
        name: str,
        position: Union[list, str, None] = None,
        guaranteed: Union[list, str, None] = None,
        also: Union[list, str, None] = None,
        part: Union[list, str, None] = None,
        synonyms: Union[Tuple[str, str], None] = None,
    ):
        """
        Create a new group definition by extending this one

        :param name:  name of the new group
        :param position: list of positional elements
        :param guaranteed: list of required elements
        :param also:    list of optional elements
        :param part: list of groups that can be included in this one
        :param synonyms: list of tuples defining synonym for elements
                         e,g, [("ano","year"),...]
        :return: new group class



        """
        new_group = type(name, (cls,), {})
        new_group._name = name
        # todo: k,v in kwargs if in cls set if not error
        if type(position) is str:
            position = [position]
        if type(guaranteed) is str:
            guaranteed = [guaranteed]
        if type(also) is str:
            also = [also]
        if position is not None:
            new_group._position = position
        else:
            new_group._position = list(cls._position)
        if guaranteed is not None:
            new_group._guaranteed = guaranteed
        else:
            new_group._guaranteed = list(cls._guaranteed)
        if also is not None:
            new_group._also = also
        else:
            new_group._also = list(cls._also)
        if part is not None:
            new_group._part = part
        else:
            new_group._part = list(cls._part)
        if synonyms is not None:
            try:
                for word, synonym in synonyms:
                    sym_class = KElement.get_class_for(synonym)
                    if sym_class is None:
                        msg = f"synonym error {synonym} is unkown"
                        raise ValueError(msg)
                    else:
                        # this creates a new KElement class
                        # named "word" that inherits from the KElement
                        # class of synonym
                        sym_class.extend(word)
            except ValueError:
                msg = "synonyms must be list of tuples"
                "e.g. [('ano','date').."
                raise (ValueError(msg))

        new_group._extends = cls

        return new_group

    @classmethod
    def get_subclasses(cls):
        """Generator for subclasses of this group"""
        for subclass in cls.__subclasses__():
            yield from subclass.get_subclasses()
            yield subclass

    @classmethod
    def all_subclasses(cls):
        """List of all the subclasses of this group"""
        return list(cls.get_subclasses())

    @classmethod
    def is_kgroup(cls, g):
        """True g is an instance of a subclass of KGroup"""
        return "KGroup" in [c.__name__ for c in type(g).mro()]

    @classmethod
    def elements_allowed(cls) -> set:
        """Set of  Elements allowed in this Group"""
        return set(cls._guaranteed).union(set(cls._also)).union(cls._position)

    @classmethod
    def allow_as_element(
        cls, ename: Union[str, List[str]], guaranteed=False, also=True, position=None
    ):
        """
        Add element or list to list of allowed elements for this group.
        Optionally define if element(s) is positional,
        required (guaranteed) or optional
        :param ename:  name of element
        :param guaranteed: if True this is element is added to list of required elements.
        :param also: if True this element is optional (default)
        :param position: int, this is a positional element, at this position (0 = first position)
        :return: List of allowed elements
        """
        if type(ename) is List:
            for e in ename:
                cls.allow_as_element(
                    e, guaranteed=guaranteed, position=position, also=also
                )
            return
        elif type(ename) is str:
            if guaranteed:
                if ename not in cls._guaranteed:
                    cls._guaranteed.append(ename)
            if position is not None:
                if ename in cls._position:
                    cls._position.remove(ename)
                cls._position.insert(position, ename)
            if ename not in cls.elements_allowed():
                cls._also.append(ename)
        else:
            raise TypeError("first argument must be string or list of strings")
        return

    @classmethod
    def allow_as_part(cls, g: Union[str, type]):
        """Allow g to be enclosed as part of this group.

        Arguments:
            g: the name of a group, or a subclass of KGroup.
               A string or class.
        """
        if g not in cls._part:
            cls._part.append(g)

    @classmethod
    def inc_sequence(cls):
        KGroup._global_sequence += 1
        return KGroup._global_sequence

    @classmethod
    def inc_line(cls):
        KGroup._global_line += 1
        return KGroup._global_line

    def __init__(self, *args, **kwargs):
        """Creates a new instance of group with setting the value of elements.

        Args:
            *args: values for positional arguments
            **kwargs: values for optional elements.

        Example:
            ``ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")``

        Use element_check=False to turn off checking of element names

        """
        self._containsd: dict = {}
        self.level = 1
        self.line = 1
        self.order = 1
        self._element_check = True
        self._elementsd = {}
        self._inside = None

        if len(args) > len(self._position):
            raise ValueError("Too many positional elements")
        n = 0
        # set the positional arguments according to "_position"
        for arg in args:
            e = self._position[n]
            # setattr(self, e, KElement(e, arg))
            self[e] = arg  # this will go through __setitem__
            n = n + 1
        # keyword arguments must be in one the element lists
        for k, v in kwargs.items():
            if k == "element_check":
                self._element_check = v
            else:
                if self._element_check and not self.is_allowed_as_element(k):
                    raise ValueError(f"Element not allowed: {k}")
                self[k] = v
        # test if the compulsory (guaranteed) elements are present
        for g in self._guaranteed:
            if getattr(self, g, None) is None:
                raise TypeError(
                    f"{self.kname}: element {g} in _guaranteed "
                    f"is missing or with None value"
                )

    def include(self, group: Type["KGroup"]):
        """Include a group. `group`, or its class, must in _part list or
            extend a class in the part list.

        Returns self so it is possible to chain: g.include(g2).include(g3)"""

        allowed = self.is_allowed_as_part(group)
        if allowed is None:
            raise ValueError(f"Group {self.kname} cannot contain {group.kname}")

        group.level = self.level + 1
        group.line = KGroup.inc_line()
        group.order = KGroup.inc_sequence()

        # Hook to before input processing in the group being included
        if hasattr(group, "before_include") and callable(group.before_include):
            if not group.before_include(self):
                raise TypeError(
                    f"{group} includding aborted by "
                    f"group.before_include(self)"
                    f" returning False"
                )

        # new style, dictionary based
        k = self._containsd.keys()
        if allowed in k:
            self._containsd[allowed].append(group)
        else:
            self._containsd[allowed] = [group]
        group.inside = self
        # Hook to after input processing in the group being included
        if hasattr(group, "after_include") and callable(group.after_include):
            group.after_include(self)
        return self

    def before_include(self, container_group):
        """Method called before this group is included into another
        through KGroup.include(KGroup)."""

        if self.id is None:
            if container_group.id is None:
                raise ValueError(
                    "A group with no id cannot be included in another "
                    "group also without id"
                )
            gid = f"{container_group.id}-{self.order:02d}-{self.kname[0:3]}"
            self["id"] = gid
            return True

        return True

    def after_include(self, group):
        """Method called after a new group is included in this one
        through KGroup.include(KGroup)."""
        pass

    def is_allowed_as_part(self, group):
        """Test if a group can be included in the current one.

        For a group to be allowed for inclusion one of 3 conditions necessary:
            1. the kname of the group is in self._pars
            2. the type of the group is in self._pars
            3. the type of the group inherits from a type in self._pars

        Return key under which the group is allowed (kname, type or super type)
        Return None if not allowed
        """
        if not self.is_kgroup(group):
            raise TypeError("Argument must be subclass of KGroup")
        if group.kname not in self._part:
            allowed_classes = [c for c in self._part if type(c) is not str]
            super_classes = type(group).mro()
            r = list(set(super_classes).intersection(set(allowed_classes)))
            if len(r) == 0:
                allowed = None
            else:
                allowed = r[0]  # kname?
        else:
            allowed = group.kname

        return allowed

    def is_allowed_as_element(self, element_name):
        """
        Test if this element is allowed in this group.

        For an element to be allowed one the following must be true:

            1. part of KGroup._builtin
            2. part of position list
            3. part of guarenteed list
            4. part of also list

        Note that this function is unaffected by self._element_check

        :param element_name: name of element to check

        :return: True if element allowed False otherwise
        """
        all_elements = (
            self._builtin_elements + self._position + self._guaranteed + self._also
        )
        return element_name in all_elements

    def includes(self, group: Type[Union[str, Type["KGroup"]]] = None) -> list:
        """Returns included groups.

        Groups are returned by the order in _pars.

        :todo:  this would better be a generator, yield instead of extend.

        :param str group: filter by group name
        """
        if group is not None:
            if group in self._containsd.keys():
                return self._containsd[group]
            else:
                if type(group) is str:
                    gname = group
                elif KGroup.is_kgroup(group):
                    gname = group.kname

                inc_by_part_order = []
                classes_in_contains = [
                    c for c in self._containsd.keys() if hasattr(c, "_name")
                ]
                for class_in_contains in classes_in_contains:
                    if class_in_contains._name == gname:
                        inc_by_part_order.extend(self._containsd[class_in_contains])
                return inc_by_part_order
        else:  # no specific subgroup, we return by pars order
            inc_by_part_order = []
            for p in self._part:
                if p in self._containsd.keys():
                    inc_by_part_order.extend(self._containsd[p])

            return inc_by_part_order

    def attr(
        self,
        the_type: Union[str, KElement, Tuple[str, str, str]],
        value: Union[str, KElement, Tuple[str, str, str]],
        date: Union[str, KElement, Tuple[str, str, str]],
        obs=None,
    ):
        """Utility function to include a KAttribute in this KGroup

        The call::

            KGroup.attr('age','25','2021-08-08',obs='in May')

        is short hand for::

            KGroup.include(KAttr('age','25','2021-08-08',obs='in May'))

        Params google style

        :param str or tuple the_type: core or (core,org,comment)
        :param str or tuple value: core or (core,org,comment)
        :param str date: date as string in Kleio format, or (date,org,comment)
        :param str obs: options observation field

        """
        ka = self._attr_class
        self.include(ka(the_type, value, date=date, obs=obs))
        return self

    def rel(
        self,
        the_type: Union[str, tuple],
        value: Union[str, tuple],
        destname: Union[str, tuple],
        destination: Union[str, tuple],
        date: Union[str, tuple] = None,
        obs: str = None,
    ):
        """include a relation in this KGroup"""
        kr = self._rel_class
        self.include(kr(the_type, value, destname, destination, date=date, obs=obs))

    def to_kleio(self, indent="") -> str:
        """Return a kleio representation of the group."""
        return self.__str__(indent=indent, recurse=True)

    def to_dict(
        self,
        allow_none: bool = False,
        include_str: bool = False,
        include_kleio: bool = False,
        redundant_keys: bool = True,
        include_builtin: bool = True,
    ):
        """Return group information as a dict.

        Params:
            allow_none bool = Include null values (default False)

            :param allow_none: Include null values (default False)
            :param include_str: include a string represention of each element
                                with keys [elementname]_str, the value will include
                                # and % if necessary
            :param include_kleio: include a kleio representation of each element
                                  with keys [elementname]_kleio; this is similar
                                  to *include_str* but the value also contains the
                                  element name
            :param redundant_keys: include redundant keys (see bellow)
            :param include_builtin: include also elements like line,level,... etc...
            :return: a dictionary with the structure bellow

            *Keys of returned dict*

            :group[element]:
                core value of element; also group[element_core]
            :group[element_comment]:
                comment aspect of element
            :group[element_original]:
                original aspect of element
            :group[element_str]:
                 if *include_str=True*, a string representation of elementm(with # and % if necessary);
            :group[element_kleio]:
                if *include_kleio=True*, a kleio representation in the form ``element=string``
            :group[includes]:
                list of enclosed groups
            :group[includes][subgroup]:
                list of enclosed groups of type subgroup


        If *redundant_keys=True* enclosed subgroups can also be accessed
        in the plural form, if no name conflict with existing elements::

                group['persons'] == group['includes']['persons']
                group['person']['id1'] ==
                        [p for p in group['includes']['persons']
                        if p.id='id1'][0]



        :todo: add first(), last() where includes is allowed::
                    group['first']['person'] = group['includes']['person'][0]

        """
        kd = dict()
        kd["kleio_group"] = self._name
        elements_to_include = self.elements_allowed()
        if include_builtin:
            els = elements_to_include.union(set(self._builtin_elements)) - set(
                ["inside"]
            )
        for e in els:
            v: KElement = getattr(self, e, None)
            if v is not None:
                if issubclass(type(v), KElement):
                    core, comment, original = v.to_tuple()
                    kd[e] = core
                    kd[e + "_core"] = core
                    kd[e + "_comment"] = comment
                    kd[e + "_original"] = original
                    if include_str:
                        kd[e + "_str"] = str(v)
                    if include_kleio:
                        kd[e + "_kleio"] = v.to_kleio()
                else:
                    kd[e] = v
        if not allow_none:
            kd = dict([(key, value) for key, value in kd.items() if value is not None])
        # we now includes subgroups
        ki = dict()
        # we now collect subgroups by name
        included = list(self.includes())
        for i in included:
            n = i.kname
            if n not in ki.keys():
                ki[n] = [
                    i.to_dict(
                        include_str=include_str,
                        include_kleio=include_kleio,
                        include_builtin=include_builtin,
                        redundant_keys=redundant_keys,
                    )
                ]
            else:
                ki[n].append(
                    i.to_dict(
                        include_str=include_str,
                        include_kleio=include_kleio,
                        include_builtin=include_builtin,
                        redundant_keys=redundant_keys,
                    )
                )
        if len(ki) > 0:
            kd["includes"] = ki
            # if there are no name conflicts and plural form
            # so g['includes']['act'] can be accessed as
            #    g['acts']
            if redundant_keys:
                for subgroup in ki.keys():
                    if subgroup + "s" not in self.elements_allowed():
                        kd[subgroup + "s"] = ki[subgroup]
                        # we include subgroup indexed by id
                        # so we can have source['act']['ac010]['person']['p01']
                        for group in ki[subgroup]:
                            gid = group.get("id", None)
                            if (
                                gid is not None
                                and subgroup not in self.elements_allowed()  # noqa
                            ):
                                if subgroup not in kd.keys():
                                    kd[subgroup] = dict()
                                kd[subgroup][gid] = group
        return kd

    def to_json(self):
        return json.dumps(
            self.to_dict(
                include_str=False,
                include_kleio=False,
                redundant_keys=False,
                include_builtin=True,
            ),
            indent=4,
            allow_nan=False,
        )

    @property
    def get(self):
        return self.to_dict()

    def to_dots(self):
        return Box(self.to_dict())

    @property
    def dots(self):
        """
        Allows easy referencing of the dictionary representation of the group.

        It is very usefull in list comprehensiona, e.g.:

          >> 'Diamantina' in [ls.value for ls in person.dots.lss
                                if ls.type == 'nome-geografico']

          >> [ls.value for ls in person.dots.lss
                        if ls.type == 'nome-geografico']

        :return:
        """
        return self.to_dots()

    def __str__(self, indent="", recurse=False):
        sname = getattr(self, "_name", self.__class__.__name__)
        s = str(sname) + "$"
        first = True
        out = []
        for e in self._position:
            v: KElement = getattr(self, e, None)
            if v is not None:
                if not first:
                    s = s + "/" + v.to_kleio(name=False)
                else:
                    s = s + v.to_kleio(name=False)
                    first = False
                out.append(e)
        more = sorted(
            list(
                set(self._guaranteed)
                .union(set(self._also))
                .union(self._position)
                .difference(out)
            )
        )
        # print(more)
        if "obs" in more:  # we like obs elements at the end
            more.remove("obs")
            more.append("obs")
        for e in more:
            m: Union[KElement, str] = getattr(self, e, None)
            if m is not None and (
                type(m) is str
                and m > ""  # noqa
                or (issubclass(type(m), KElement) and m.to_kleio() > "")  # noqa
            ):
                # m contains data, lets output
                if issubclass(type(m), KElement):
                    v = m.to_kleio()
                else:
                    v = KElement(e, m).to_kleio()
                if not first:
                    s = s + f"/{v}"
                else:
                    s = s + f"{v}"
                    first = False

        if recurse:
            for g in self.includes():
                s = s + nl + g.__str__(indent + " ", recurse=recurse)
        return textwrap.indent(s, indent)

    def __getitem__(self, arg):
        if self._element_check and arg not in self.elements_allowed():
            raise ValueError("Element does not exist in group")
        return getattr(self, arg)

    def __setitem__(self, arg, value):
        if self._element_check and not self.is_allowed_as_element(arg):
            raise ValueError(f"Element not allowed: {arg}")
        el = self.pack_as_kelement(arg, value)
        setattr(self, arg, el)
        self._elementsd[arg] = el

    def pack_as_kelement(self, arg, value, element_class=None):
        """Packs value as a KElement with name arg

        :param arg: name of element
        :param value: value of element; can be a KElement, a tuple
                      (core, cooment, original) or a value
        :param element_class: class of element as string; if none arg is used to find class

        TODO: the question is what is the class of the KElement to be stored
        if value is a KElement then it already has a class
        """
        # TODO: this is wrong. if value is a KElement it should be stored as such

        if element_class is None:
            kelement = KElement.get_class_for(arg)
        else:
            kelement = KElement.get_class_for(element_class)
        if kelement is None and isinstance(value, KElement):
            if isinstance(value.element_class, KElement):
                kelement = value.element_class
            else:
                kelement = KElement.get_class_for(value.element_class)
        if kelement is None:  # if there is no KElement class we create it
            kelement = KElement.extend(arg)
            warnings.warn(
                f"Created a KElement class for {arg}. "
                f"Better to create explicit or provide "
                f" synonyms= in group creation.",
                stacklevel=2,
            )
            # we get KElement class that matches the name
            # this is how we handle localized name of elements that
            # have a builtin meaning or are referred to by standard names
            # in PomSomMapping
        if isinstance(value, KElement):
            el = kelement(
                core=value.core, comment=value.comment, original=value.original
            )
        else:
            comment = None
            original = None
            if type(value) is tuple and len(value) == 3:
                core, comment, original = value
            else:
                core = value
            el = kelement(arg, core=core, comment=comment, original=original)
        return el

    def unpack_from_kelement(self, value):
        """
        if value is a KElement return core if not return value as is.

        Useful to obtain the core value in elements that normally have
        no comment or original.

        :param value:
        :return:
        """
        if not isinstance(value, KElement):  # we did not get a KElement
            return value
        else:  # we got a KElement object
            return value.core

    def get_core(self, element, default=None):
        """get_core(element_name [, default])
        Returns the core value of an element
        """
        try:
            core = self.unpack_from_kelement(self[element])
        except ValueError:
            core = None
        except AttributeError:
            core = None
        if core is None:
            return default
        else:
            return core

    def get_id(self):
        """Return the id of the group"""
        return self.unpack_from_kelement(self.id)

    def get_element_for_column(self, colspec, default=None):
        """
        Return the value of an element that matches a specific column in the
        database.

        An element matches a column if its name is equal to the column name
        or if it is an instance of KElement subclass with the same name.

        :param colspec: name of column, or name of POMClassAttributes
        :param default: default value if not element found
        :return: KElement, or whatever in default.

        """
        el: KElement
        for (
            name,
            el,
        ) in (
            self._elementsd.items()
        ):  # same name as column or in ancestors # noqa: E501
            if name == colspec:
                return el
        # Handles synonyms created by subclassing core KElements
        for el in self._elementsd.values():  # if name in inherited names
            if colspec in el.inherited_names():
                return el
        # handles multiple subclassing of core KElements
        for (
            el
        ) in (
            self._elementsd.values()
        ):  # check if there are alternative classes # noqa: E501
            # all classes for colspec
            targets = KElement.get_classes_for(colspec)
            # other classes for el
            alternatives = KElement.get_classes_for(el.name)
            # now check if there is a common path
            #   collect all the ancestors of all the classes for this el
            alt_ancestors = [(sc, sc.inherits_from()) for sc in alternatives]
            #   check if any of colspec classes are there
            for _alternative, ancestors in alt_ancestors:
                common = set(ancestors).intersection(set(targets))
                if len(common) > 0:
                    return el
        return default
