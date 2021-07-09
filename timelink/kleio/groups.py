from dataclasses import dataclass,fields,field
from typing import Any, ClassVar
from typing_extensions import ParamSpecKwargs
from timelink.kleio.utilities import entity_to_kleio,format_obs,quote_long_text,kleio_escape


#print('__file__={0:<35} | __name__={1:<20} | __package__={2:<20}'.format(__file__,__name__,str(__package__)))

# Usar metadata para assinalar os elementos posicionais e outras informações do gacto
# extrair a função de formatação kleio para uma função externa e evocar no __str__
# a função externa to_kleio(Entity) usa a informação de metadados para formatar
# Os valores dos campos podem ser uma string ou um tuple (cor,org,comment)
# Para maneira de gerir inheritance com dataclasses 
# ver https://stackoverflow.com/questions/51575931/class-inheritance-in-python-3-7-dataclasses


class KElement():
    """

    KElement(name,core,comment=,original=)
     Elements have a name, and three possible values:
     a core value, an optional comment and an optional original wording.

    Parameters
    ----------

    name: str 
          The name of the element
    core: str or tuple (core,comment,original).
          The core value of the Element. 
          KElement('el','core-value',comment='a comment', original='ah commant') 
          can be shortened as 
          KElement('el', ('coure-value','a comment','a command'))



    """
    name: str
    core: Any # must have a str representation.
    comment: str = None
    original: str = None
    _source = None

    def __init__(self,name,core,**kwargs):
        self.name = name
        if type(core) is tuple and len(core == 3):
            self.core = core[0]
            self.comment = core[1]
            self.original = core[2]
        else:
            self.core = core
            self.comment = kwargs.get('comment',None)
            self.comment = kwargs.get('original',None)

    def __str__(self):
        c = self.core
        cc = self.comment
        o = self.original
        if c == None:
            c = ''
        else:
            c = quote_long_text(str(c))
        if cc == None:
            cc = ''
        else:
            cc = '#'+quote_long_text(str(cc))
        if o == None:
            o = ''
        else:
            o = '%'+quote_long_text(str(o))       
        return c+cc+o

    def to_kleio(self):
        return self.name+'/'+str(self)

class KGroup():
    """
    KGroup(*positional_elements ,**more_elements)

    Abstract Kleio Group.
    Extend this class and set default values for _name, and at least for one 
    of _position, _guaranteed, _also. 
    Optionally set _part to list of allowed enclosed groups.
    Those default values will allow proper initialization.
    
    Parameters
    ----------
    *positional_elements : tuple
                        Values will be stored as elements with names specified by `_position`
    *more_elements: dict
                        argument names mut be part of _position,_guaranteed or _also

    """

    id : str = '*id*'
    contains = []
    _name: str = 'kgroup'
    _position:  list = []
    _guaranteed: list = []
    _also: list = []
    _part: list =[]

    def __init__(self,*args,**kwargs):
        assert len(args) <= len(self._position), 'Too many positional elements'
        n = 0
        for arg in args:
            e = self._position[n]
            setattr(self,e,KElement(e,arg))
            n = n+1
        for (k,v) in kwargs.items():
            assert k in self._position+self._guaranteed+self._also, f'Element not allowed: {k}'
            setattr(self,k,KElement(e,v))
        for g in self._guaranteed:
            assert getattr(self,g,None) != 'Element {g} missing or with None value'
        
    def insert(self, group):
        assert group.name in self._part, 'Group {self.name} cannot contain {group.name}'
        self.contains.append(group)

    def __str__(self):
        s = self._name+'$'
        first = True
        out = []
        for e in self._position:
            v = getattr(self,e,None)
            if v != None:
                if not first:
                    s = s + '/' + str(v)
                else:
                    s = s + str(v)
                    first = False
                out.append(e)
        more = set(self._guaranteed).union(set(self._also)).union(self._position).difference(out)
        print(more)
        for e in more:
            m = getattr(self,e,None)
            if m != None:
                if not first:
                    s = s + f'/{e}={str(m)}'
                else:
                    s = s + f'{e}={str(m)}'
                    first = False
        return s

class KSource(KGroup):
    """ A Historical Source
    KSource(id,year,type,ref,loc=,obs=,ref=)

    Parameters
    ----------
    ref: str The call number or "cota" of the source
    loc: str Location, archive, name
    
    """
    _name = 'historical-source'
    _guaranteed = ['id']
    _also = ['type','date','year','loc','ref','obs','replace']
    _position = ['id','year','type','ref']
    _part = ['historical-act']

    pass


        


@dataclass(init=False)
class Entity():
    id: str = field(metadata={'positional':True})
    attributes: list = field(compare=False,init=False,default_factory=lambda: [])
    relations_out:  list = field(compare=False,init=False,default_factory=lambda: [])
    relations_in:  list = field(compare=False,init=False,default_factory=lambda: [])
    contains: list= field(compare=False,init=False,default_factory=lambda: [])
    obs: str = field(compare=False,init=False,default=None)
    kgroup:  str  = field(compare=False, init=False,default=None)
    nentities: ClassVar[int] = 0

    def __init__(self,*args,**kwargs):    
        #print('type of this object: ',str.lower(type(self).__name__))
        positional = [f.name for f in fields(self) if f.metadata.get('positional',False) == True ]
        #print(f'Defined posicional args: {positional}')
        #print(f'{args=}')
        assert len(positional) == len(args), f'Wrong number of args: expected {len(positional)}({positional}) got {len(args)} ({args})'
        n = 0
        for arg in args:
            #print(f'Setting {n} to {arg}')
            setattr(self,positional[n],arg)
            n=n+1
        optional = [f.name for f in fields(self) if f.metadata.get('positional',False) == False ]
        #print(f'Defined optional args: {optional}')
        #print(f'__init__ optional args: {kwargs.keys()}')
        for kw in kwargs.keys():
            assert kw in optional, f'Bad parameter: {kw}, must be one of {optional}'

        self.attributes = []
        self.relations_in = []
        self.relations_out = []
        self.contains = []
        self.obs = None
        for f in fields(self):
            if f.metadata.get('positional',False) == False :
                if f.name in kwargs.keys():
                    setattr(self,f.name,kwargs[f.name])
                elif not hasattr(self,f.name):
                    setattr(self,f.name,None)
        Entity.nentities =+ 1
        if self.id == None:
            self.id = str(Entity.nentities)
        if self.kgroup == None:
            self.kgroup = str.lower(type(self).__name__)

    def __str__(self):
        return entity_to_kleio(self)

@dataclass(init=False)
class Attribute():
    entity: Entity 
    atype: str = field(metadata={'kleio_name':'type','positional':True}) # attribute type
    value: str = field(metadata={'positional':True})
    date: str = field(default=None, metadata={'positional':False})
    obs: str = field(compare=False,default=None)
    kgroup:  str  = field(compare=False, default='atr')
    natr: ClassVar[int] = 0

    def __init__(self,entity,atype,value,date=None,obs=None,kgroup=None):
        print(f'attribute-date: {date}')
        self.entity=entity
        self.atype=atype
        self.value=value
        self.date=date
        self.kgroup=kgroup
        if self.entity != None:
            self.entity.attributes.append(self)
        Attribute.natr =+ 1
        self.id = str(Attribute.natr)
        if self.kgroup == None:
            self.kgroup = str.lower(type(self).__name__)

            
    def __str__(self):
        knames_dict = {f.name: f.metadata.get('kleio_name') for f in fields(self)}
        print(f'knames_dict: {knames_dict}')
        s = self.kgroup+'$'+self.atype+'/'+quote_long_text(self.value)
        if self.date != None:
            dname = knames_dict.get('date','date')
            if dname == None:
                dname='date'
            s=s+f'/{dname}='+self.date  
        if self.obs != None and self.obs>' ':
            s = s + format_obs(self.obs)
        return s


@dataclass
class Relation():
    origin: Entity 
    destination: Entity
    rtype: str = field(metadata={'kleio_name':'type','positional':True}) # attribute type
    value: str = field(metadata={'positional':True})
    dest_name: str = field(default='*none*',metadata={'positional':True})
    date: str = field(default=None, metadata={'positional':False})
    obs: str = field(compare=False,default=None)
    kgroup:  str  = field(compare=False, default='rel')
    nrel: ClassVar[int] = 0

    def __post_init__(self):
        if self.origin != None:
            self.origin.relations_out.append(self)
        if self.destination != None:
            self.destination.relations_in.append(self)
        Relation.nrel =+ 1
        self.id = str(Relation.nrel)

    def __str__(self):
        s = self.kgroup+'$'+self.rtype+'/'+self.value+'/'+self.dest_name+'/'+self.destination.id
        if self.date != None:
            s=s+'/date='+self.date
        if self.obs != None and self.obs>' ':
            s = s + format_obs(self.obs)
        return s


@dataclass(init=False)
class Source(Entity): 
    """ 
    Source(id,stype=SourceType,date=SourceDate,loc=Archive,ref=call number,year=YearofSource,replace=IdOfSourceToReplace)
    
    A Kleio source. When printed (or when converted to string) produces a valid kleio representation.

    Parameters
    ----------
    id: str
        Unique id for the source
    stype: str, default='Historical source'
        Type of source (parish registers, notarial records, ... )
    date: str, default=None
        Date in timelink date range format, eg: >1537:1914-11-14
    loc: str, default=None
        Name of archive holding the sources
    ref: str, default=None
        Call number, reference of the source in archive, "cota"
    year: str,  default=None
        Deprecated, replacement for Date, use single year in `date`
    replace: str,  default=None
        Id of another source that this one will replace on import
    obs: str,  default=None
        Note on the source. Multi line content possible, enclose on triple quotes
    kpath: str, default=None
        Path of the kleio file associated with this source
    kgroup: str, default=source
        Name used for kleio representation of this source
    """
    stype: str = field(compare=False, default=None,metadata={'kleio_name':'type','positional':False}) # source type
    date: str  = field(compare=False,default=None, metadata={'positional':False})
    loc: str = field(compare=False,default=None, metadata={'positional':False})
    ref: str  = field(compare=False,default=None, metadata={'positional':False})
    year: str  = field(compare=False,default=None, metadata={'positional':False})
    replace: str = field(compare=False,default=None, metadata={'positional':False})
    kpath: str  = field(compare=False, default=None, metadata={'positional':False})# path to a kleio file with the content of this source

        

@dataclass(init=False)
class Act(Entity):
    """
    Act(id,day,month,year,atype=ActType,date=Date,loc=Loc,ref=Ref)

    A historical act. When printed (or when converted to string) produces a valid kleio representation.

    Parameters
    ----------

    day,month,year: str
        Used for single day acts (like parish registers). For more flexibilidade use `date` instead
    atype: str, default='Historical act'
    date: str, default=None
        Date in timelink date range format, eg: >1537:1914-11-14
    loc: str, default=None
        Name of archive holding the sources
    ref: str, default=None
        Call number, reference of the source in archive, "cota"
    """

    day: int = field(compare=False, metadata={'positional':True})
    month: int = field(compare=False, metadata={'positional':True})
    year: int = field(compare=False, metadata={'positional':True})
    atype: str = field(compare=False, default=None,metadata={'kleio_name':'type','positional':False}) # act type
    date: str  = field(compare=False,default=None, metadata={'positional':False})
    loc: str = field(compare=False,default=None, metadata={'positional':False})
    ref: str  = field(compare=False,default=None, metadata={'positional':False})

@dataclass(init=False)
class Person(Entity):
    name: str = field(compare=False, metadata={'positional':True})
    sex: str  = field(compare=False, metadata={'positional':False})
    id: str = field(compare=True,metadata={'positional':False})
  