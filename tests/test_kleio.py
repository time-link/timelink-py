"""
Test for timelink.kleio package
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
import pytest

from timelink.kleio.groups import KElement, KPerson, KLs
from timelink.kleio.utilities import quote_long_text
from timelink.kleio.groups import KGroup, KKleio, KSource, KAct


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
    e = KElement('el',None,comment=None,original=None)
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
    assert y in x._contains, "include failed"


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
    assert y in x._contains, \
        "include failed after class allowed as part"


def test_kgroup_attr():
    p = KPerson('joaquim', 'm')
    p.attr('location', 'macau', '2021')
    attrs = p.includes()
    assert len(attrs) > 0, "attribute not included in KGroup"


def test_kgroup_to_kleio(kgroup_source_dev):
    kgroup_source_dev
    s = 'source$dev-1718/date=1721-10-10:1723-07-09/loc=AUC/ref="III/D,1,4,4,55"/replace=visita-1718/type=Episcopal visitation/obs=Transcrition available, manuscript.'
    assert kgroup_source_dev.to_kleio() == s, "Bad group representation"


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
    assert '    ls$location/Macau/2021-07-15' in p.to_kleio().splitlines(), \
        "ls failed to show in person"
