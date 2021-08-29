"""
Test for timelink.kleio package
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
import pytest

from timelink.kleio.groups import KElement, KPerson, KLs, KAbstraction, KAtr
from timelink.kleio.utilities import quote_long_text
from timelink.kleio.groups import KGroup, KKleio, KSource, KAct


@pytest.fixture
def kgroup_nested() -> KSource:
    """Returns a nested structure"""
    ks = KSource('s1', type='test', loc='auc', ref='alumni', obs='Nested')
    ka1 = KAct('a1', 'test-act', date='2021-07-16',
               day=16, month=7, year=2021,
               loc='auc', ref='p.1', obs='Test Act')
    ks.include(ka1)
    ka2 = KAct('a2', 'test-act', date='2021-07-17',
               day=17, month=7, year=2021,
               loc='auc', ref='p.2', obs='Test Act')
    ks.include(ka2)
    p1 = KPerson('Joaquim', 'm', 'p01')
    p2 = KPerson('Margarida', 'f', 'p02')
    p3 = KPerson('Pedro', 'm', 'p03')
    ka1.include(p1)
    ka1.include(p2)
    ka1.include(p3)
    p4 = KPerson('Maria', 'f', 'p04')
    p5 = KPerson('Manuel', 'm', 'p05')
    p6 = KPerson('João', 'm', 'p06')
    ka2.include(p4)
    ka2.include(p5)
    ka2.include(p6)
    return ks


@pytest.fixture
def kgroup_source_dev() -> KSource:
    """
    KSource('dev-1718',
                 type='Episcopal visitation',
                 loc='AUC',
                 ref='III/D,1,4,4,55',
                 date='1721-10-10:1723-07-09',
                 replace='visita-1718',
                 obs=\"""Transcrition available, manuscript.\""")
    """
    ks = KSource('dev-1718',
                 type='Episcopal visitation',
                 loc='AUC',
                 ref='III/D,1,4,4,55',
                 date='1721-10-10:1723-07-09',
                 replace='visita-1718',
                 obs="""Transcrition available, manuscript.""")
    return ks


def test_kelement():
    e = KElement('id', '0001')
    assert e.name == 'id', "Failed name setting"
    assert e.core == '0001', "Failed single core value"


def test_kelement_tuple():
    e = KElement('name',
                 ('Joaquim Carvalho',
                  'Family name added in the margin',
                  'Joachim Carvº',
                  ))
    assert e.name == 'name', "Failed name setting"
    assert e.core == 'Joaquim Carvalho', "Failed core  from tuple"
    assert e.original == 'Joachim Carvº', "Failed original from tuple"
    assert e.comment == 'Family name added in the margin', \
        "Failed comment from tuple"


def test_kelement_dict():
    e = KElement('name',
                 ('Joaquim Carvalho',
                  'Family name added in the margin',
                  'Joachim Carvº',
                  ))
    ed = e.to_dict(name=True)
    assert ed['name'] == 'name', "Failed name from dict"
    assert ed['core'] == 'Joaquim Carvalho', "Failed core  from dict"
    assert ed['original'] == 'Joachim Carvº', "Failed original from dict"
    assert ed['comment'] == 'Family name added in the margin', \
        "Failed comment from dict"


def test_kelement_dict2():
    e = KElement('name',
                 ('Joaquim Carvalho',
                  'Family name added in the margin',
                  'Joachim Carvº',
                  ))
    ed = e.to_dict(name=False)
    assert len(ed) == 3, \
        "Failed dictionary without name"


def test_kelement_optionals():
    e = KElement('name', 'Joaquim Carvalho', original='Joachim Carvº',
                 comment="Family name added in the margin")
    assert e.name == 'name', "Failed name setting"
    assert e.core == 'Joaquim Carvalho', "Failed core from optionals"
    assert e.original == 'Joachim Carvº', "Failed original from optional"
    assert e.comment == 'Family name added in the margin', \
        "Failed comment from optional"


def test_kelement_to_str_1():
    e = KElement('name', 'Joaquim Carvalho')
    assert str(e) == 'Joaquim Carvalho'


def test_kelement_to_str_2():
    e = KElement('name', 'Joaquim \nCarvalho')
    assert str(e) == quote_long_text(e.core), \
        "str() failed with multiple line core"


def test_kelement_to_str_3():
    e = KElement('name', 'Joaquim Carvalho', original='Joachim Cº')
    assert str(e) == 'Joaquim Carvalho%Joachim Cº', \
        "str() failed with original option"


def test_kelement_to_str_4():
    e = KElement('name', 'Joaquim Carvalho',
                 comment="Family name added in the margin")
    assert str(e) == 'Joaquim Carvalho#Family name added in the margin', \
        "str() failed with optional comment"


def test_kelement_is_empty():
    e = KElement('el', None, comment=None, original=None)
    assert e.is_empty(), "Did not detect empty element"


def test_kelement_is_empty_2():
    e = KElement('el', 'something', comment=None, original=None)
    assert not e.is_empty(), "Did not detect empty element"


def test_kelement_is_empty_3():
    e = KElement('el', None, comment='comment', original=None)
    assert not e.is_empty(), "Did not detect empty element"


def test_kelement_to_kleio():
    e = KElement('name', 'Joaquim Carvalho', original='Joachim Carvº',
                 comment="Carvº added in the margin")
    assert e.to_kleio() == \
           'name=Joaquim Carvalho#Carvº added in the margin%Joachim Carvº', \
           "bad kleio representation of Element"


def test_kgroup_extend():
    kfonte: KGroup = KGroup.extend('fonte',
                                   position=['id'],
                                   also=['tipo',
                                         'data',
                                         'ano',
                                         'obs',
                                         'substitui'])
    afonte = kfonte('f001', ano=2021, tipo='teste')
    assert afonte.id.core == 'f001', 'could not extend group and instantiate'


def test_kgroup_include():
    p = KPerson('joaquim', 'm', 'jrc')
    with pytest.raises(TypeError):
        p.include('xpto')


def test_kgroup_subclasses():
    n = KPerson.extend('n')
    m = KPerson.extend('m')
    f = KPerson.extend('f')
    sub_classes = (n, m, f)
    p = n('joaquim', 'm', '01')
    sc = KPerson.all_subclasses()
    assert len(sc) == 3 and len(sub_classes) == 3, \
        "Failed to register subclasses"
    assert KPerson.is_kgroup(p), "Failed is_kgroup test"


def test_allow_as_part_1():
    class Kx(KGroup):
        pass

    class Ky(KGroup):
        pass

    Kx._name = 'kx'
    Kx._guaranteed = ['id']

    Ky._name = 'ky'
    Ky._guaranteed = ['id']
    Ky._position = ['id']

    x = Kx(id='x001')
    y = Ky('y001')

    print(x.to_kleio())
    print(y.to_kleio())

    with pytest.raises(ValueError):
        x.include(y), "include should have failed"

    Kx.allow_as_part('ky')
    x.include(y)
    assert y in x.includes(), "include failed"


def test_allow_as_part_2():
    class Kx(KGroup):
        pass

    class Ky(KGroup):
        pass

    Kx._name = 'kx'
    Kx._guaranteed = ['id']

    Ky._name = 'ky'
    Ky._guaranteed = ['id']
    Ky._position = ['id']

    x = Kx(id='x001')
    y = Ky('y001')

    Kx.allow_as_part(Ky)
    x.include(y)
    assert y in list(x.includes()), \
        "include failed after class allowed as part"


def test_allow_as_part_3():
    Kx = KGroup.extend('kx')
    Ky = KGroup.extend('ky')
    Kx.allow_as_part(Ky)
    l1 = len(Kx._part)
    Kx.allow_as_part(Ky)
    Kx.allow_as_part(Ky)
    Kx.allow_as_part(Ky)
    l2 = len(Kx._part)

    assert l1 == l2, "allow_as_part added repeated group"


def test_allow_as_part_4():
    n: KPerson = KPerson.extend('n', position=['name', 'sex'],
                                guaranteed=['name'])
    j = n('joaquim', 'm')
    pn = KPerson.extend('pn', position=['name'], guaranteed=['name'])
    n.allow_as_part(pn)
    j.include(pn('Arménio'))
    assert len(j.includes()) == 1, "Could not insert sub group"


def test_includes_group():
    n: KPerson = KPerson.extend('n', position=['name', 'sex'],
                                guaranteed=['name'])
    j = n('joaquim', 'm')
    pn = KPerson.extend('pn', position=['name'], guaranteed=['name'])
    n.allow_as_part(pn)
    j.include(pn('Arménio'))
    j.attr('residencia', 'Macau', date='2021-08-08', obs='Taipa')

    for pai in j.includes():
        print("pai: ", pai)

    lpn = list(j.includes(group=pn))
    pai = lpn[0]
    np = pai.name.core
    assert np == 'Arménio', "Could not retrieve group by name"


def test_includes_by_part_order():
    n: KPerson = KPerson.extend('n', position=['name', 'sex'],
                                guaranteed=['name'])
    j = n('joaquim', 'm')
    pn = KPerson.extend('pn', position=['name'], guaranteed=['name'])
    n.allow_as_part(pn)
    j.include(pn('Arménio'))
    j.attr('residencia', 'Macau', date='2021-08-08', obs='Taipa')
    inc = list(j.includes())
    assert inc[-1].kname == 'pn', "included groups not by part order"


def test_includes_no_arg():
    kleio = KKleio('gacto2.str')
    ks = KSource('s1', type='test', loc='auc', ref='alumni', obs='Nested')
    kleio.include(ks)
    ka1 = KAct('a1', 'test-act', date='2021-07-16',
               day=16, month=7, year=2021,
               loc='auc', ref='p.1', obs='Test Act')
    ks.include(ka1)
    kdots = kleio.dots
    sources = kdots.sources
    source = sources[0]
    acts = source.acts
    act = acts[0]
    assert act.id == 'a1', "Problem with dot notation"
    assert kdots.sources[0].acts[
               0].id == 'a1', "Could not use dots notation for includes"
    # pretty neat!
    assert kdots.source.s1.act.a1.type == 'test-act', \
        "group-id dot notation failed"


def test_kgroup_attr():
    p = KPerson('joaquim', 'm')
    p.attr('location', 'macau', '2021')
    attrs = list(p.includes())
    assert len(attrs) > 0, "attribute not included in KGroup"


def test_kgroup_to_kleio(kgroup_source_dev):
    s = 'source$dev-1718/date=1721-10-10:1723-07-09/loc=AUC/' \
        'ref="III/D,1,4,4,55"/replace=visita-1718/type=Episcopal visitation' \
        '/obs=Transcrition available, manuscript.'
    assert kgroup_source_dev.to_kleio() == s, "Bad group representation"


def test_kgroup_to_kleio_empty_1():
    p = KPerson('joaquim', 'm', 'jrc', obs='')
    assert p.to_kleio() == 'person$joaquim/m/jrc'


def test_kgroup_get_item():
    p = KPerson('joaquim', 'm', 'jrc', obs='')
    assert p['name'].core == 'joaquim'


def test_kgroup_set_item():
    p = KPerson('joaquim', 'm', 'jrc', obs='')
    p['name'] = ('joaquim', 'aka jrc', 'jota')
    assert p.name.core == 'joaquim', "__setitem__ failed"
    assert p.name.comment == 'aka jrc', "__setitem__ failed"
    assert p.name.original == 'jota', "__setitem__ failed"


def test_kgroup_get(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.get["includes"]["act"][0]["id"] == 'a1', \
        "Failed nested dictionary"


def test_kgroup_get_id(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.get["act"]['a1']['date'] == '2021-07-16', \
        "Failed nested dictionary"


def test_kgroup_get2(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.get["acts"][0]["id"] == 'a1', \
        "Failed nested dictionary"


def test_kgroup_dots(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.includes.act[0].id == 'a1', \
        "Failed dots retrieval"


def test_kgroup_dots2(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.acts[0].id == 'a1', \
        "Failed dots retrieval"


def test_kgroup_dots3(kgroup_nested):
    kgroup_nested
    the_dots = kgroup_nested.dots
    anact: KGroup = the_dots.acts[0]
    inc = anact.includes
    name = inc.person[0].name
    assert name == 'Joaquim', "Failed dots retrieval"


def test_kgroup_dots4(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.acts[0].persons[0].name == 'Joaquim', \
        "Failed dots retrieval"


def test_kgroup_dots_id(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.act.a1.person.p01.name == 'Joaquim', \
        "Failed dots retrieval"


def test_kgroup_core_value(kgroup_source_dev):
    assert kgroup_source_dev.id.core == 'dev-1718', \
        "Failed to retrieve core value"


def test_kgroup_get_core(kgroup_source_dev):
    assert kgroup_source_dev.get_core('id') == 'dev-1718', \
        "Failed to retrieve core value"


def test_kgroup_get_core2(kgroup_source_dev):
    assert kgroup_source_dev.get_core('year', 2021) == 2021, \
        "Failed to retrieve default for core value"


def test_kgroup_2(kgroup_source_dev):
    assert kgroup_source_dev.id.core == 'dev-1718', \
        "Failed to retrieve core value"


def test_person_ls_rel():
    p = KPerson('joaquim', 'm', 'jrc', obs='aka JRC')
    p.include(KLs('location', 'Macau', '2021-07-15'))
    assert ' ls$location/Macau/2021-07-15' in p.to_kleio().splitlines(), \
        "ls failed to show in person"


def test_kleio_stru():
    # We specialize the kleio groups for this purpose,
    # using definitions already in gacto2.str
    kleio = KKleio
    assert kleio is not None
    fonte = KSource.extend('fonte',
                           also=['tipo', 'data', 'ano', 'substitui', 'loc',
                                 'ref', 'obs'])
    lista = KAct.extend('lista', position=['id', 'dia', 'mes', 'ano'],
                        guaranteed=['id', 'ano', 'mes', 'dia'],
                        also=['data', 'tipo', 'loc', 'obs'])
    auc = KAbstraction.extend('auc', position=['name', ''],
                              also=['level', 'id'], guaranteed=['id'])
    n = KPerson.extend('n', position=['nome', 'sexo'],
                       guaranteed=['id', 'nome', 'sexo'],
                       also=['mesmo_que', 'obs'])
    pai = KPerson.extend('pai', position=['nome'], guaranteed=['id', 'nome'],
                         also=['mesmo_que', 'obs'])
    mae = KPerson.extend('mae', position=['nome'], guaranteed=['id', 'nome'],
                         also=['mesmo_que', 'obs'])
    n.allow_as_part(pai)
    n.allow_as_part(mae)
    ls = KLs.extend('ls', position=['type', 'value'], also=['data', 'obs'])
    atr = KAtr.extend('atr', position=['type', 'value'], also=['data', 'obs'])

    kf = KKleio()
    f = fonte('f001', tipo='auc-tests')
    kf.include(f)
    l: KGroup = lista('l001', 11, 2, 2021, data='1537-1913', tipo='auc-list',
                      loc='A')
    f.include(l)
    a = auc('alumni-record', 'archeevo-record', id='xpto')
    l.include(a)
    j = n('joaquim', 'm', obs='em macau')
    j.include(ls('uc', 'início', data=2021))
    j.include(atr('xauc', 'dsd'))
    l.include(j)
    l2 = lista('l003', 18, 2, 2021, data='1537-1913', tipo='auc-list', loc='B')
    f.include(l2)
    m = n('manuel', 'm', obs='em Berlin')
    m.include(ls('uc', 'fim', data=2021))
    l2.include(m)

    assert j.nome.core == 'joaquim'
