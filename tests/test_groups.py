"""
Test for timelink.kleio package
(c) Joaquim Carvalho 2021.
MIT License, no warranties.
"""
import logging

import pytest

from timelink.kleio.groups import (
    KElement,
    KPerson,
    KAbstraction,
    KGroup,
    KKleio,
    KSource,
    KAct,
)
from timelink.kleio.groups.katr import KAtr
from timelink.kleio.groups.kelement import KDate, KDay, KMonth, KYear, KType, KReplace
from timelink.kleio.groups.kls import KLs
from timelink.kleio.utilities import quote_long_text


@pytest.fixture
def kgroup_nested() -> KSource:
    """Returns a nested structure"""
    ks = KSource(
        "s1", type="test", loc="auc", date="2021-07-16", ref="alumni", obs="Nested"
    )
    ka1 = KAct(
        "a1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)
    ka2 = KAct(
        "a2",
        "test-act",
        date="2021-07-17",
        day=17,
        month=7,
        year=2021,
        loc="auc",
        ref="p.2",
        obs="Test Act",
    )
    ks.include(ka2)
    p1 = KPerson("Joaquim", "m", "p01")
    p1.attr("residencia", "Macau", date="2021-12-11")
    p2 = KPerson("Margarida", "f", "p02")
    p2.attr("residencia", "Trouxemil", date="2020-10-18")
    p1.rel(
        "parentesco", "marido", p2.name, p2.id, date="2006-01-4", obs="Ilha Terceira"
    )
    p3 = KPerson("Pedro", "m", "p03")
    p3.attr("residencia", "Rua Arménio RC", date="2021-10-21")
    ka1.include(p1)
    ka1.include(p2)
    ka1.include(p3)
    p4 = KPerson("Maria", "f", "p04")
    p5 = KPerson("Manuel", "m", "p05")
    p6 = KPerson("João", "m", "p06")
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
    ks = KSource(
        "dev-1718",
        type="Episcopal visitation",
        loc="AUC",
        ref="III/D,1,4,4,55",
        date="1721-10-10:1723-07-09",
        replace="visita-1718",
        obs="""Transcrition available, manuscript.""",
    )
    return ks


def test_kelement():
    e = KElement("id", "0001")
    assert e.name == "id", "Failed name setting"
    assert e.core == "0001", "Failed single core value"


def test_element_empty():
    e = KElement(name="empty", core=None, original=None, comment=None)
    k = e.to_kleio(name=False)
    assert k == ""
    k = e.to_kleio(name=True)
    assert k == ""


def test_element_invisible():
    k_invisible = KElement.extend("invisible_")
    ki = k_invisible(name="invisible", core="a")
    k = ki.to_kleio()
    assert k == ""
    k = ki.to_kleio(force_show=True)
    assert k == "invisible=a"


def test_element_class_extend():
    # extend date to have a synonym in another language
    kdata_pt = KDate.extend("data")
    data_class = kdata_pt
    data_class_name = data_class.__name__
    data_class_kname = data_class.name
    assert data_class_name == data_class_kname == "data"
    data_mro = data_class.__mro__
    assert data_mro
    all_element_types = KElement.all_subclasses()
    inherited_names = [
        ke.name for ke in data_mro if ke is not object and ke.name is not None
    ]
    assert len(all_element_types) > 0
    assert len(inherited_names) > 0
    date_class = data_class.__base__
    d = kdata_pt(core="2021-12-12")
    assert d.name == "data"
    # new KElement type should keep original class
    assert d.extends(date_class.name)
    # we use a different name for the date
    fda = kdata_pt.extend("fim_de_ano")
    nd = fda("2021-12-31")
    assert nd.name == "fim_de_ano"
    assert nd.core == "2021-12-31"
    # but still is as date
    fds_names = nd.inherited_names()
    assert "date" in fds_names
    assert nd.extends(date_class.name)


def test_element_class_extend2():
    date_class = KDate.name
    group_with_date = KGroup.extend("gdate", position="date")
    gd = group_with_date("2021-12-12")
    assert gd.date.core == "2021-12-12"
    assert gd.date.element_class == date_class


def test_kelement_subclasses():
    classes = KElement.all_subclasses()
    assert len(classes) > 0


def test_kelement_subclasses2():
    classes = KElement.all_subclasses()
    element_names = [el.name for el in classes]  # noqa: F841
    assert len(classes) > 0
    assert len(element_names) > 0


def test_kelement_extend():
    KAno: KYear = KYear.extend("ano")
    annus_horribilis = KAno(1580)
    assert annus_horribilis.core + 1 == 1581


def test_kelement_extend_2():
    KAno: KYear = KYear.extend("ano")
    assert KAno.name == "ano"


def test_kelement_extend_3():
    KAno: KYear = KYear.extend("ano")
    annus_horribilis = KAno(1580)
    assert annus_horribilis.extends("ano")
    assert annus_horribilis.extends("year")


def test_kelement_extend_4():
    KAno: KYear = KYear.extend("ano")
    assert KAno in KElement.get_classes_for("ano")
    assert KAno.name == "ano"


def test_kelement_extend_6():
    """many competing classes for element get the one that matches column"""
    KAno: KYear = KYear.extend("ano")
    KAno2 = KElement.extend("ano")
    KAno3 = KAno2.extend("ano")
    KAno4 = KAno3.extend("ano")
    gano = KGroup.extend("gano", position=["ano"])
    testing: KGroup = gano(2021)
    ano = testing.get_element_for_column(KYear.name)
    assert KAno.name == KAno4.name  # just to use the variables
    assert ano.core == 2021  # get the more specialized


def test_kdate():
    d = KDate("2021-12-10")
    assert d.name == "date"


def test_kdate2():
    d = KDate("2021-12-10")
    assert d.name == "date"


def test_kday1():
    day = KDay(24)
    assert day.name == "day"


def test_kday1b():
    day = KDay(0)
    assert day.core == 0


def test_kday2():
    day = KDay("24", comment="it is a nice day", original="twenty-four")
    assert day.name == "day"
    assert day.comment == "it is a nice day"
    assert day.original == "twenty-four"


def test_kday2b():
    day = KDay(("24", "it is a nice day", "twenty-four"))
    assert day.name == "day"
    assert day.core + 1 == 25
    assert day.comment == "it is a nice day"
    assert day.original == "twenty-four"


def test_kday3():
    with pytest.raises(ValueError):
        day = KDay("32")
        assert day.core == "32"


def test_kday4():
    with pytest.raises(ValueError):
        day = KDay("31x")
        assert day.core == "31x"


def test_kday5():
    day = KDay(None)
    assert day.core == 0


def test_month1():
    month = KMonth(("05", "it is a nice month", "May"))
    assert month.name == "month"
    assert month.core + 1 == 6
    assert month.comment == "it is a nice month"
    assert month.original == "May"


def test_month2():
    month = KMonth("12")
    assert month.core + 1 == 13


def test_month3():
    with pytest.raises(ValueError):
        month = KMonth(14)
        assert month.core == 14


def test_month4():
    month = KMonth(0)
    assert month.core == 0, "Did not accept zero value"


def test_month5():
    month = KMonth(None)
    assert month.core == 0, "Did not accept zero value"


def test_year_1():
    year = KYear(2021)
    assert year.core == 2021


def test_kelement_tuple():
    e = KElement(
        "name",
        (
            "Joaquim Carvalho",
            "Family name added in the margin",
            "Joachim Carvº",
        ),
    )
    assert e.name == "name", "Failed name setting"
    assert e.core == "Joaquim Carvalho", "Failed core  from tuple"
    assert e.original == "Joachim Carvº", "Failed original from tuple"
    assert e.comment == "Family name added in the margin", "Failed comment from tuple"


def test_kelement_dict():
    e = KElement(
        "name",
        (
            "Joaquim Carvalho",
            "Family name added in the margin",
            "Joachim Carvº",
        ),
    )
    ed = e.to_dict(name=True)
    assert ed["name"] == "name", "Failed name from dict"
    assert ed["core"] == "Joaquim Carvalho", "Failed core  from dict"
    assert ed["original"] == "Joachim Carvº", "Failed original from dict"
    assert (
        ed["comment"] == "Family name added in the margin"
    ), "Failed comment from dict"


def test_kelement_dict2():
    e = KElement(
        "name",
        (
            "Joaquim Carvalho",
            "Family name added in the margin",
            "Joachim Carvº",
        ),
    )
    ed = e.to_dict(name=False)
    assert len(ed) == 3, "Failed dictionary without name"


def test_kelement_optionals():
    e = KElement(
        "name",
        "Joaquim Carvalho",
        original="Joachim Carvº",
        comment="Family name added in the margin",
    )
    assert e.name == "name", "Failed name setting"
    assert e.core == "Joaquim Carvalho", "Failed core from optionals"
    assert e.original == "Joachim Carvº", "Failed original from optional"
    assert (
        e.comment == "Family name added in the margin"
    ), "Failed comment from optional"


def test_kelement_to_str_1():
    e = KElement("name", "Joaquim Carvalho")
    assert str(e) == "Joaquim Carvalho"


def test_kelement_to_int():
    e = KElement("line", "254")
    assert int(e) + 1 == 255


def test_kelement_to_kleio():
    e = KElement("name", "Joaquim \nCarvalho")
    assert e.to_kleio(name=False) == quote_long_text(
        e.core
    ), "str() failed with multiple line core"


def test_kelement_kleio_2():
    e = KElement("name", "Joaquim Carvalho", original="Joachim Cº")
    assert (
        e.to_kleio() == "name=Joaquim Carvalho%Joachim Cº"
    ), "str() failed with original option"


def test_kelement_kleio_3():
    e = KElement("name", "Joaquim Carvalho", comment="Family name in the margin")
    assert (
        e.to_kleio(name=True) == "name=Joaquim Carvalho#Family name in the margin"
    ), "str() failed with optional comment"


def test_kelement_is_empty():
    e = KElement("el", None, comment=None, original=None)
    assert e.is_empty(), "Did not detect empty element"


def test_kelement_is_empty_2():
    e = KElement("el", "something", comment=None, original=None)
    assert not e.is_empty(), "Did not detect not empty element"


def test_kelement_is_empty_3():
    e = KElement("el", None, comment="comment", original=None)
    assert not e.is_empty(), "Did not detect not empty element"


def test_kelement_to_kleio_2():
    e = KElement(
        "name",
        "Joaquim Carvalho",
        original="Joachim Carvº",
        comment="Carvº added in the margin",
    )
    assert (
        e.to_kleio() == "name=Joaquim Carvalho#Carvº added in the margin%Joachim Carvº"
    ), "bad kleio representation of Element"


def test_kgroup_extend():
    kfonte: KGroup = KGroup.extend(
        "fonte",
        position=["id"],
        also=["tipo", "data", "ano", "obs", "substitui"],
        synonyms=[("tipo", "type"), ("data", "date"), ("ano", "year")],
    )
    afonte = kfonte("f001", ano=2021, tipo="teste")
    assert afonte.id.core == "f001", "could not extend group and instantiate"


def test_kgroup_extend2():
    # these create localized version of original elements
    KData = KDate.extend("data")  # noqa: F841
    KAno = KYear.extend("ano")  # noqa: F841
    KTipo = KType.extend("tipo")  # noqa: F841
    KSubstitui = KReplace.extend("substitui")  # noqa: F841
    kfonte: KGroup = KGroup.extend(
        "fonte", position=["id"], also=["tipo", "data", "ano", "obs", "substitui"]
    )
    afonte = kfonte("f001", data="2021-12-09", ano=2021, tipo="teste", substitui="f001")
    assert afonte.data.extends("date")
    year_value = afonte.get_element_for_column("year")
    assert 2021 == year_value.core
    assert KData.__name__ == "data"
    assert KAno.__name__ == "ano"
    assert KTipo.__name__ == "tipo"
    assert KSubstitui.__name__ == "substitui"


def test_kroup_elements_allowed():
    my_group: KGroup = KGroup.extend(
        "mygrou", position="id", also=["nome", "genero", "telefone"]
    )
    selements = sorted(my_group.elements_allowed())
    assert selements == ["genero", "id", "nome", "telefone"], "wrong element list"


def test_kroup_allow_as_element():
    my_group: KGroup = KGroup.extend(
        "mygroup", position="id", also=["nome", "genero", "telefone"]
    )
    selements = sorted(my_group.elements_allowed())
    assert selements == ["genero", "id", "nome", "telefone"], "wrong element list"

    my_group.allow_as_element("profissao", also=True)
    selements = sorted(my_group.elements_allowed())
    assert selements == [
        "genero",
        "id",
        "nome",
        "profissao",
        "telefone",
    ], "wrong element list after allow_as_element"

    my_group.allow_as_element("idade", guaranteed=True)
    selements = sorted(my_group.elements_allowed())
    assert selements == [
        "genero",
        "id",
        "idade",
        "nome",
        "profissao",
        "telefone",
    ], "wrong element list after allow_as_element"
    assert my_group._guaranteed == ["idade"]

    my_group.allow_as_element("nome", position=0)
    assert my_group._position == ["nome", "id"]


def test_kgroup_include():
    p = KPerson("joaquim", "m", "jrc")
    with pytest.raises(TypeError):
        p.include("xpto")


def test_kgroup_subclasses():
    n = KPerson.extend("n")
    m = KPerson.extend("m")
    f = KPerson.extend("f")
    sub_classes = (n, m, f)
    p = n("joaquim", "m", "01")
    sc = KPerson.all_subclasses()
    assert len(sc) == 3 and len(sub_classes) == 3, "Failed to register subclasses"
    assert KPerson.is_kgroup(p), "Failed is_kgroup test"


def test_allow_as_part_1():
    class Kx(KGroup):
        pass

    class Ky(KGroup):
        pass

    Kx._name = "kx"
    Kx._guaranteed = ["id"]

    Ky._name = "ky"
    Ky._guaranteed = ["id"]
    Ky._position = ["id"]

    x = Kx(id="x001")
    y = Ky("y001")

    # print(x.to_kleio())
    # print(y.to_kleio())

    with pytest.raises(ValueError):
        x.include(y), "include should have failed"

    Kx.allow_as_part("ky")
    x.include(y)
    assert y in x.includes(), "include failed"


def test_allow_as_part_2():
    class Kx(KGroup):
        pass

    class Ky(KGroup):
        pass

    Kx._name = "kx"
    Kx._guaranteed = ["id"]

    Ky._name = "ky"
    Ky._guaranteed = ["id"]
    Ky._position = ["id"]

    x = Kx(id="x001")
    y = Ky("y001")

    Kx.allow_as_part(Ky)
    x.include(y)
    assert y in list(x.includes()), "include failed after class allowed as part"


def test_allow_as_part_3():
    Kx = KGroup.extend("kx")
    Ky = KGroup.extend("ky")
    Kx.allow_as_part(Ky)
    l1 = len(Kx._part)
    Kx.allow_as_part(Ky)
    Kx.allow_as_part(Ky)
    Kx.allow_as_part(Ky)
    l2 = len(Kx._part)

    assert l1 == l2, "allow_as_part added repeated group"


def test_allow_as_part_4():
    n: KPerson = KPerson.extend("n", position=["name", "sex"], guaranteed=["name"])
    j = n("joaquim", "m", id="jrc")
    pn = KPerson.extend("pn", position=["name"], guaranteed=["name"])
    n.allow_as_part(pn)
    j.include(pn("Arménio"))
    assert len(j.includes()) == 1, "Could not insert sub group"


def test_includes_group():
    N: KPerson = KPerson.extend("n", position=["name", "sex"], guaranteed=["name"])
    j: N = N("joaquim", "m", id="jrc")  # type: ignore
    j.attr("residencia", "macau", date="2021-12-16")
    atr1 = KAtr("residencia", "Coimbra", "2020-09-20")
    atr2 = KAtr("hobby", "caligrafia", "2020-09-20")
    j.include(atr1)
    j.include(atr2)
    j.attr("idade", "63", date="2021-08-08", obs="Taipa")
    PN = KPerson.extend("pn", position=["name"], guaranteed=["name"])
    N.allow_as_part(PN)
    j.include(PN("Arménio"))
    j.attr("profissao", "professor", date="2021-08-08", obs="Taipa")

    lpn = list(j.includes(group="pn"))
    pai = lpn[0]
    np = pai.name.core
    assert np == "Arménio", "Could not retrieve group by name"


def test_includes_by_part_order():
    n: KPerson = KPerson.extend("n", position=["name", "sex"], guaranteed=["name"])
    j = n("joaquim", "m", id="jrc")
    pn = KPerson.extend("pn", position=["name"], guaranteed=["name"])
    n.allow_as_part(pn)
    j.include(pn("Arménio"))
    j.attr("residencia", "Macau", date="2021-08-08", obs="Taipa")
    inc = list(j.includes())
    assert inc[-1].kname == "pn", "included groups not by part order"


def test_includes_no_arg():
    kleio = KKleio("gacto2.str")
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    kleio.include(ks)
    ka1 = KAct(
        "a1",  # id
        "test-act",  # type
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)
    kdots = kleio.dots
    sources = kdots.sources
    source = sources[0]
    acts = source.acts
    act = acts[0]
    assert act.id == "a1", "Problem with dot notation"
    assert (
        kdots.sources[0].acts[0].id == "a1"
    ), "Could not use dots notation for includes"
    # pretty neat!
    assert kdots.source.s1.act.a1.type == "test-act", "group-id dot notation failed"


def test_kgroup_attr():
    p = KPerson("joaquim", "m", id="joaq")
    p.attr("location", "macau", "2021")
    attrs = list(p.includes())
    assert len(attrs) > 0, "attribute not included in KGroup"


def test_kgroup_to_kleio(kgroup_source_dev):
    s = (
        "source$dev-1718/date=1721-10-10:1723-07-09/loc=AUC/"
        'ref="III/D,1,4,4,55"/replace=visita-1718/type=Episcopal visitation'
        "/obs=Transcrition available, manuscript."
    )
    kleio = kgroup_source_dev.to_kleio()
    assert kleio == s, "Bad group representation"


def test_kgroup_to_kleio_empty_1():
    p = KPerson("joaquim", "m", "jrc", obs=None)
    assert p.to_kleio() == "person$joaquim/m/jrc"


def test_kgroup_get_item():
    p = KPerson("joaquim", "m", "jrc", obs="")
    assert p["name"].core == "joaquim"


def test_kgroup_get_item_check_el():
    p = KPerson("joaquim", "m", "jrc", obs="")
    with pytest.raises(ValueError):
        p["nome"], "get inexistent element should raise error"


def test_kgroup_get_item_no_check_el():
    p: KPerson = KPerson("joaquim", "m", "jrc", obs="")
    p._element_check = False
    KElement.extend("profissao")
    p["profissao"] = "Professor"
    assert p["profissao"], "Could not enter unchecked element"


def test_kgroup_set_item():
    p = KPerson("joaquim", "m", "jrc", obs="")
    p["name"] = ("joaquim", "aka jrc", "jota")
    assert p.name.core == "joaquim", "__setitem__ failed"
    assert p.name.comment == "aka jrc", "__setitem__ failed"
    assert p.name.original == "jota", "__setitem__ failed"


def test_kgroup_set_item_check_el():
    p = KPerson("joaquim", "m", "jrc", obs="")
    with pytest.raises(ValueError):
        p["profissao"] = "professor", "set illegal element should raise error"


def test_kgroup_get(kgroup_nested):
    kgroup_nested
    assert (
        kgroup_nested.get["includes"]["act"][0]["id"] == "a1"
    ), "Failed nested dictionary"


def test_kgroup_line_seq_level():
    kk = KKleio("gacto2.str")
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    kk.include(ks)
    ka1 = KAct(
        "a1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)
    line = ks.line
    assert line == 2, "Failed line update"
    act = ks.includes("act")[0]
    assert act.level == 3, " Failed level update"
    p1 = KPerson("Joaquim", "m", "p01")
    ka1.include(p1)
    person = act.includes("person")[0]
    assert person.level == 4, " Failed level update"
    assert person.order == 4, " Failed sequence update"


def test_kgroup_line_seq_level_2():
    kk = KKleio("gacto2.str")
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    kk.include(ks)
    ka1 = KAct(
        "a1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)


def test_kgroup_set_element_more_than_once():
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    assert ks.id.core == "s1"
    ks["id"] = "s1-changed"
    assert ks.id.core == "s1-changed"


def test_kgroup_inside():
    kk = KKleio("gacto2.str")
    ks = KSource("s1", type="test", loc="auc", ref="alumni", obs="Nested")
    kk.include(ks)
    ka1 = KAct(
        "a1",
        "test-act",
        date="2021-07-16",
        day=16,
        month=7,
        year=2021,
        loc="auc",
        ref="p.1",
        obs="Test Act",
    )
    ks.include(ka1)
    assert ks.inside is kk, "Failed inside builtin"
    assert ka1.inside is ks, "Failed inside builtin"


def test_kgroup_get_nested_dict_get(kgroup_nested):
    kgroup_nested
    act = kgroup_nested.get["act"]
    assert act["a1"]["date"] == "2021-07-16", "Failed nested dictionary"


def test_kgroup_get_nested_dict_get2(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.get["acts"][0]["id"] == "a1", "Failed nested dictionary"


def test_kgroup_dots(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.includes.act[0].id == "a1", "Failed dots retrieval"


def test_kgroup_dots2(kgroup_nested):
    kgroup_nested
    assert kgroup_nested.dots.acts[0].id == "a1", "Failed dots retrieval"


def test_kgroup_dots3(kgroup_nested):
    kgroup_nested
    the_dots = kgroup_nested.dots
    anact: KGroup = the_dots.acts[0]
    inc = anact.includes
    name = inc.person[0].name
    assert name == "Joaquim", "Failed dots retrieval"


def test_kgroup_dots4(kgroup_nested):
    kgroup_nested
    assert (
        kgroup_nested.dots.acts[0].persons[0].name == "Joaquim"
    ), "Failed dots retrieval"


def test_kgroup_dots_id(kgroup_nested):
    kgroup_nested
    assert (
        kgroup_nested.dots.act.a1.person.p01.name == "Joaquim"
    ), "Failed dots retrieval"


def test_KPerson_to_json():
    p1 = KPerson("Joaquim", "m", "p01")
    p1.attr("residencia", "Macau", date="2021-12-11")
    p2 = KPerson("Margarida", "f", "p02")
    json_string = p1.to_json()
    assert json_string
    json_string = p2.to_json()
    assert json_string
    p1.rel(
        "parentesco", "marido", p2.name, p2.id, date="2006-01-4", obs="Ilha Terceira"
    )
    json_string = p1.to_json()
    assert json_string


def test_kgroup_to_json(kgroup_nested):
    for inner in kgroup_nested.includes():
        logging.log(logging.DEBUG, f"json for {inner.kname}")
        logging.log(logging.DEBUG, f"json {inner.to_json()}")
    json_string = kgroup_nested.to_json()

    assert json_string, "Could not produce json"


def test_kgroup_core_value(kgroup_source_dev):
    assert kgroup_source_dev.id.core == "dev-1718", "Failed to retrieve core value"


def test_kgroup_get_core(kgroup_source_dev):
    assert (
        kgroup_source_dev.get_core("id") == "dev-1718"
    ), "Failed to retrieve core value"


def test_kgroup_get_core2(kgroup_source_dev):
    assert (
        kgroup_source_dev.get_core("year", 2021) == 2021
    ), "Failed to retrieve default for core value"


def test_kgroup_2(kgroup_source_dev):
    assert kgroup_source_dev.id.core == "dev-1718", "Failed to retrieve core value"


def test_person_ls_rel():
    p = KPerson("joaquim", "m", "jrc", obs="aka JRC")
    p.include(KLs("location", "Macau", "2021-07-15"))
    assert (
        " ls$location/Macau/2021-07-15" in p.to_kleio().splitlines()
    ), "ls failed to show in person"


def test_synonyms_1():
    # We can map new elements to existing ones in group creation
    kleio = KKleio
    assert kleio is not None
    fonte: KSource = KSource.extend(
        "fonte",
        also=["tipo", "data", "ano", "substitui", "loc", "ref", "obs"],
        synonyms=[("tipo", "type")],
    )
    assert fonte is not None
    tipo = KElement.get_class_for("tipo")
    assert tipo is not None


def test_synonyms_2():
    # We can map new elements to existing ones in group creation
    kleio = KKleio
    assert kleio is not None
    with pytest.raises(ValueError):
        fonte: KSource = KSource.extend(
            "fonte",
            also=["tipo", "data", "ano", "substitui", "loc", "ref", "obs"],
            synonyms=[("tipo", "typer")],  # no KElement typer
        )
        assert fonte is not None  # this should never be reached


def test_kleio_stru():
    # We specialize the kleio groups for this purpose,
    # using definitions already in gacto2.str
    kleio = KKleio
    assert kleio is not None
    fonte = KSource.extend(
        "fonte",
        also=["tipo", "data", "ano", "substitui", "loc", "ref", "obs"],
        synonyms=[("tipo", "type"), ("data", "date"), ("ano", "year")],
    )
    lista = KAct.extend(
        "lista",
        position=["id", "dia", "mes", "ano"],
        guaranteed=["id", "ano", "mes", "dia"],
        also=["data", "tipo", "loc", "obs"],
        synonyms=[
            ("tipo", "type"),
            ("dia", "day"),
            ("mes", "month"),
            ("data", "date"),
            ("ano", "year"),
        ],
    )
    auc = KAbstraction.extend(
        "auc", position=["name", "type"], also=["level", "id"], guaranteed=["id"]
    )
    n = KPerson.extend(
        "n",
        position=["nome", "sexo"],
        guaranteed=["id", "nome", "sexo"],
        also=["mesmo_que", "obs"],
        synonyms=[("nome", "name"), ("sexo", "sex"), ("mesmo_que", "same_as")],
    )
    pai = KPerson.extend(
        "pai",
        position=["nome"],
        guaranteed=["nome"],
        also=["mesmo_que", "obs"],
        synonyms=[("nome", "name"), ("mesmo_que", "same_as")],
    )
    mae = KPerson.extend(
        "mae",
        position=["nome"],
        guaranteed=["nome"],
        also=["mesmo_que", "obs"],
        synonyms=[("nome", "name"), ("mesmo_que", "same_as")],
    )
    n.allow_as_part(pai)
    n.allow_as_part(mae)
    ls = KLs.extend(
        "ls",
        position=["type", "value"],
        also=["data", "obs", "entity"],
        synonyms=[("data", "date")],
    )
    atr = KAtr.extend(
        "atr",
        position=["type", "value"],
        also=["data", "obs", "entity"],
        synonyms=[("data", "date")],
    )

    kf = KKleio()
    f = fonte("f001", tipo="auc-tests")
    kf.include(f)
    l: KGroup = lista("l001", 11, 2, 2021, data="1537-1913", tipo="auc-list", loc="A")
    f.include(l)
    a = auc("alumni-record", "archeevo-record", id="xpto")
    l.include(a)
    j: KGroup = n("joaquim", "m", obs="em macau", id="jrc")
    j.include(ls("uc", "início", data=2021))
    j.include(atr("xauc", "dsd"))
    l.include(j)
    l2 = lista("l003", 18, 2, 2021, data="1537-1913", tipo="auc-list", loc="B")
    f.include(l2)
    m = n("manuel", "m", obs="em Berlin", id="mrc")
    m.include(ls("uc", "fim", data=2021))
    l2.include(m)
    json_string = j.to_json()
    assert j.nome.core == "joaquim"
    assert len(json_string) > 0
