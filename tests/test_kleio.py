"""
Test for timelink.kleio package
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
from timelink.kleio.groups import KElement
from timelink.kleio.utilities import quote_long_text
from timelink.kleio.groups import KSource


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


def test_kelement_to_kleio():
    e = KElement('name', 'Joaquim Carvalho', original='Joachim Carvº',
                 comment="Carvº added in the margin")
    assert e.to_kleio() == \
           'name=Joaquim Carvalho#Carvº added in the margin%Joachim Carvº', \
        "bad kleio representation of Element"


def test_kgroup_1():
    ks = KSource('dev-1718',
                 type='Episcopal visitation',
                 loc='AUC',
                 ref='III/D,1,4,4,55',
                 date='1721-10-10:1723-07-09',
                 replace='visita-1718',
                 obs="""Transcrition available, manuscript."""
                 )
    print(ks.to_kleio())
    s =  'source$dev-1718/date=1721-10-10:1723-07-09/loc=AUC/ref="III/D,1,4,4,55"/replace=visita-1718/type=Episcopal visitation/obs=Transcrition available, manuscript.'
    print(s)
    assert ks.to_kleio() == s, "Bad group representation"

