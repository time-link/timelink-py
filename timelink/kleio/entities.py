"""
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from dataclasses import dataclass, field, fields
from typing import ClassVar

from timelink.kleio.utilities import entity_to_kleio, format_obs, \
    quote_long_text


@dataclass(init=False)
class Entity:
    id: str = field(metadata={'positional': True})
    attributes: list = field(compare=False, init=False,
                             default_factory=lambda: [])
    relations_out: list = field(compare=False, init=False,
                                default_factory=lambda: [])
    relations_in: list = field(compare=False, init=False,
                               default_factory=lambda: [])
    contains: list = field(compare=False, init=False,
                           default_factory=lambda: [])
    obs: str = field(compare=False, init=False, default=None)
    kgroup: str = field(compare=False, init=False, default=None)
    nentities: ClassVar[int] = 0

    def __init__(self, *args, **kwargs):
        # print('type of this object: ',str.lower(type(self).__name__))
        positional = [f.name for f in fields(self) if
                      f.metadata.get('positional', False) is True]
        # print(f'Defined posicional args: {positional}')
        # print(f'{args=}')
        assert len(positional) == len(
            args), f'Wrong number of args: expected {len(positional)}' \
                   f'({positional}) got {len(args)} ({args})'
        n = 0
        for arg in args:
            # print(f'Setting {n} to {arg}')
            setattr(self, positional[n], arg)
            n = n + 1
        optional = [f.name for f in fields(self) if
                    f.metadata.get('positional', False) is False]
        # print(f'Defined optional args: {optional}')
        # print(f'__init__ optional args: {kwargs.keys()}')
        for kw in kwargs.keys():
            assert kw in optional, f'Bad parameter: {kw}, ' \
                                   f'must be one of {optional}'

        self.attributes = []
        self.relations_in = []
        self.relations_out = []
        self.contains = []
        self.obs = None
        for f in fields(self):
            if f.metadata.get('positional', False) is False:
                if f.name in kwargs.keys():
                    setattr(self, f.name, kwargs[f.name])
                elif not hasattr(self, f.name):
                    setattr(self, f.name, None)
        Entity.nentities = + 1
        if self.id is None:
            self.id = str(Entity.nentities)
        if self.kgroup is None:
            self.kgroup = str.lower(type(self).__name__)

    def __str__(self):
        return entity_to_kleio(self)


@dataclass(init=False)
class Attribute:
    entity: Entity
    atype: str = field(
        metadata={'kleio_name': 'type', 'positional': True})  # attribute type
    value: str = field(metadata={'positional': True})
    date: str = field(default=None, metadata={'positional': False})
    obs: str = field(compare=False, default=None)
    kgroup: str = field(compare=False, default='atr')
    natr: ClassVar[int] = 0

    def __init__(self, entity, atype, value, date=None, obs=None, kgroup=None):
        print(f'attribute-date: {date}')
        self.entity = entity
        self.atype = atype
        self.value = value
        self.date = date
        self.kgroup = kgroup
        self.obs = obs
        if self.entity is not None:
            self.entity.attributes.append(self)
        Attribute.natr = + 1
        self.id = str(Attribute.natr)
        if self.kgroup is None:
            self.kgroup = str.lower(type(self).__name__)

    def __str__(self):
        knames_dict = {f.name: f.metadata.get('kleio_name') for f in
                       fields(self)}
        print(f'knames_dict: {knames_dict}')
        s = self.kgroup + '$' + self.atype + '/' + quote_long_text(self.value)
        if self.date is not None:
            dname = knames_dict.get('date', 'date')
            if dname is None:
                dname = 'date'
            s = s + f'/{dname}=' + self.date
        if self.obs is not None and self.obs > ' ':
            s = s + format_obs(self.obs)
        return s


@dataclass
class Relation:
    origin: Entity
    destination: Entity
    rtype: str = field(
        metadata={'kleio_name': 'type', 'positional': True})  # attribute type
    value: str = field(metadata={'positional': True})
    dest_name: str = field(default='*none*', metadata={'positional': True})
    date: str = field(default=None, metadata={'positional': False})
    obs: str = field(compare=False, default=None)
    kgroup: str = field(compare=False, default='rel')
    nrel: ClassVar[int] = 0

    def __post_init__(self):
        if self.origin is not None:
            self.origin.relations_out.append(self)
        if self.destination is not None:
            self.destination.relations_in.append(self)
        Relation.nrel = + 1
        self.id = str(Relation.nrel)

    def __str__(self):
        s = self.kgroup + '$' + self.rtype + '/' + self.value + '/' +\
            self.dest_name + '/' + self.destination.id
        if self.date is not None:
            s = s + '/date=' + self.date
        if self.obs is not None and self.obs > ' ':
            s = s + format_obs(self.obs)
        return s
