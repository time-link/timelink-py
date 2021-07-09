from dataclasses import dataclass,field
from timelink.kleio.groups import Person,Attribute,Relation,Source,Act

print('__file__={0:<35} | __name__={1:<20} | __package__={2:<20}'.format(__file__,__name__,str(__package__)))

 
@dataclass(init=False)
class PT_n(Person):
    sex: str = field(compare=False, default='m', metadata={'positional':False,'kleio_name':'sexo'})
    id: str = field(compare=True,metadata={'positional':False})
    kgroup: str = field(default='n',metadata={'positional':False})
    
@dataclass(init=False)
class PT_ls(Attribute):
    data: str = field(default=None, metadata={'positional':False,'kleio_name':'data'})
    kgroup: str = field(default='ls',metadata={'positional':False})
    
    def __init__(self,e,t,v,data=None,obs=None,kgroup='ls'):
        print(f'ls-data:{data}')
        super().__init__(e,t,v,date=data,obs=obs,kgroup=kgroup) # Currently we need this to pass data as date up to Attribute
        

@dataclass(init=False)
class PT_atr(Attribute):
    kgroup: str = field(default='atr',metadata={'positional':False})

    def __init__(self,e,t,v,data=None,obs=None,kgroup='atr'):
        super().__init__(e,t,v,date=data,obs=obs,kgroup=kgroup) # Currently we need this to pass data as date up to Attribute  

@dataclass(init=False)
class PT_fonte(Source):
    tipo: str = field(compare=False, default='Historical source',metadata={'kclass':'stype','positional':False}) # source type
    data: str  = field(compare=False,default=None, metadata={'positional':False,'kclass':'date'})
    loc: str = field(compare=False,default=None, metadata={'positional':False})
    ref: str  = field(compare=False,default=None, metadata={'positional':False})
    ano: str  = field(compare=False,default=None, metadata={'positional':False,'kclass':'year'})
    substitui: str = field(compare=False,default=None, metadata={'positional':False,'kclass':'replace'})
    kgroup: str = field(default='fonte',metadata={'positional':False})

@dataclass(init=False)
class PT_lista(Act):
    tipo: str = field(compare=False, default='lista',metadata={'kclass':'atype','positional':False}) # act type
    data: str  = field(compare=False,default=None, metadata={'positional':False,'kclass':'date'})
