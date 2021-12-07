import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from timelink.kleio.groups import KKleio, KSource, KAct, KAbstraction, KPerson, \
    KLs, KAtr, KGroup
from timelink.kleio.importer import import_from_xml
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.db import TimelinkDB
from timelink.mhk.models.pom_som_mapper import PomSomMapper
from timelink.mhk.models.base import Source, Person
from tests import Session

conn_string = 'sqlite:///test_db?check_same_thread=False'

@pytest.fixture(scope="module")
def dbsystem():
    db = TimelinkDB(conn_string)
    Session.configure(bind=db.engine())
    yield db
    with Session() as session:
        db.drop_db(session)

def test_import_xml(dbsystem):
    file = "./xml_data/b1685.xml"
    with Session() as session:
        import_from_xml(file,session)
        domingos_vargas = session.get(Person,'b1685.33-per6')
        assert domingos_vargas is not None, "could not get a person from file"
        entity = domingos_vargas
        for attribute in entity.attributes:
            print(f'     ls${attribute.the_type}/{attribute.the_value}/{attribute.the_date}',end='')
            if attribute.obs is not None:
                print(f'         /obs={attribute.obs}')
            else:
                print()
        for rel in entity.rels_out:
            print(f'>{rel}')
        if len(entity.rels_in)>0:
            for rel in entity.rels_in:
                    print(rel,'<')



