import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from timelink.kleio.groups import KKleio, KSource, KAct, KAbstraction, KPerson, \
    KLs, KAtr, KGroup
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.db_system import DBSystem
from timelink.mhk.models.pom_som_mapper import PomSomMapper


from timelink.mhk.models.base import Source, Person

conn_string = 'sqlite:///teste_db'


@pytest.fixture(scope="module")
def dbsystem():
    db = DBSystem(conn_string)
    db.create_db(db.conn_string)
    yield db
    db.drop_db()


def test_store_kgroup(dbsystem):
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
    j: KGroup = n('joaquim', 'm', obs='em macau')
    j.include(ls('uc', 'início', data=2021))
    j.include(atr('xauc', 'dsd'))
    l.include(j)
    l2 = lista('l003', 18, 2, 2021, data='1537-1913', tipo='auc-list', loc='B')
    f.include(l2)
    m = n('manuel', 'm', obs='em Berlin')
    m.include(ls('uc', 'fim', data=2021))
    l2.include(m)
    print(f)
    with Session(dbsystem.engine) as session:
        PomSomMapper.storeKGroup(f,bind=session)
        stmt = select(Source).where(Source.id == f.id)
        print(stmt)
        for row in session.execute(stmt):
            source_from_db: Source = row[0]
            assert source_from_db.id == f.id, "could not retrieve source"


