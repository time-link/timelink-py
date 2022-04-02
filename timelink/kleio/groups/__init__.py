"""
.. module:: groups
   :synopsis: Classes for handling Kleio groups and elements.

.. moduleauthor: Joaquim Ramos de Carvalho

Kleio Groups are the building blocks for transcription of historical sources.

The classes in this package can be used to generate Kleio sources from data
fetched from databases or read from csv or json files.

The base classes are:

KKleio
    A Kleio document. It should include a single KSource group.

KSource
    A Historical Source. Can contain a variable number
    of KAct groups.

KAct
    A historical act. Can contain a variable number
    of KPerson or KObject.

In normal usage the basic groups are extended for a particular context:



.. code-block:: python


        from timelink.kleio.groups import KKleio, KSource, KAct,
        KAbstraction, KPerson, KLs, KAtr


        kleio = KKleio

        fonte = KSource.extend('fonte',
                                also=['tipo', 'data', 'ano', 'substitui',
                                        'loc', 'ref', 'obs'])

        lista = KAct.extend('lista',
                            position=['id', 'dia', 'mes', 'ano'],
                            guaranteed=['id', 'ano', 'mes', 'dia'],
                            also=['data', 'tipo', 'loc', 'obs'])

        auc = KAbstraction.extend('auc', position=['name', ''], also=[
            'level', 'id'], guaranteed=['id'])

        n = KPerson.extend('n', position=['nome', 'sexo'], guaranteed=[
            'id', 'nome', 'sexo'], also=['mesmo_que', 'obs'])

        pai = KPerson.extend('pai', position=['nome'], guaranteed=[
            'id', 'nome'], also=['mesmo_que', 'obs'])

        mae = KPerson.extend('mae', position=['nome'], guaranteed=[
            'id', 'nome'], also=['mesmo_que', 'obs'])

        ls = KLs.extend('ls',
                        position=['type', 'value', 'data'],
                        also=['data', 'obs'])

        atr = KAtr.extend(
            'atr', position=['type', 'value', 'data'], also=['data', 'obs'])

        n.allow_as_part(pai)

        n.allow_as_part(mae)



"""

from timelink.kleio.groups.kabstraction import KAbstraction  # noqa
from timelink.kleio.groups.kobject import KObject  # noqa
from timelink.kleio.groups.kact import KAct  # noqa
from timelink.kleio.groups.kattribute import KAttribute   # noqa
from timelink.kleio.groups.kls import KLs  # noqa
from timelink.kleio.groups.katr import KAtr  # noqa
from timelink.kleio.groups.kelement import (KElement,  # noqa
                                            KDate,
                                            KDay,
                                            KMonth,
                                            KYear,
                                            KType,
                                            KValue,
                                            KId,
                                            KEntityInAttribute,
                                            KOriginInRel,
                                            KReplace,
                                            KSameAs,
                                            KXSameAs,
                                            KName,
                                            KSex,
                                            KDescription,
                                            KObs,
                                            KLevel,
                                            KLine,
                                            KOrder,
                                            KStructure,
                                            KLevel,
                                            KLoc,
                                            KRef,
                                            KDestName,
                                            KDestId,
                                            KSummary,
                                            KReplaceSourceId,
                                            )  # noqa
from timelink.kleio.groups.kgroup import KGroup  # noqa
from timelink.kleio.groups.kkleio import KKleio  # noqa
from timelink.kleio.groups.kobject import KObject  # noqa
from timelink.kleio.groups.kperson import KPerson  # noqa
from timelink.kleio.groups.krelation import KRelation  # noqa
from timelink.kleio.groups.ksource import KSource  # noqa
