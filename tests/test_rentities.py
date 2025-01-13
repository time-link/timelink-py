"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""

# pylint: disable=import-error
from pathlib import Path
import random
from typing import List

import pytest
from sqlalchemy import select
from sqlalchemy_utils import drop_database

from tests import TEST_DIR, skip_on_travis
from timelink.api.models.relation import Relation
from timelink.api.models.system import KleioImportedFile
from timelink.kleio.kleio_server import KleioServer, KleioFile
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.models.rentity import Link, REntity, LinkStatus as STATUS
from timelink.api.database import (
    TimelinkDatabase,
    start_postgres_server,
    get_postgres_container_user,
    get_postgres_container_pwd,
)

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis

db_path = Path(TEST_DIR, "sqlite")
RENTITY_DB = "rentities"
# rentity_db = ":memory:"

# set a list of files to be imported before the tests begin
TEST_FILES_DIR = str(
    Path(
        TEST_DIR,
        "timelink-home/projects/test-project/sources/reference_sources/rentities",
    )
)

kserver = None


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    if db_type == "postgres":
        start_postgres_server()
        db_user = get_postgres_container_user()
        db_pwd = get_postgres_container_pwd()

    database = TimelinkDatabase(
        db_name=db_name,
        db_type=db_type,
        db_path=db_path,
        db_url=db_url,
        db_user=db_user,
        db_pwd=db_pwd,
    )

    global kserver
    global TEST_FILES_DIR

    if kserver is None:
        # start a kleio server
        try:
            kserver = KleioServer.start(kleio_home=TEST_FILES_DIR, update=False)
        except Exception as exc:
            print(exc)
            raise

    database.set_kleio_server(kserver)

    try:
        yield database
    finally:
        database.drop_db()
        database.session().close()
        if ":memory:" not in database.db_url:
            drop_database(database.db_url)


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", RENTITY_DB, None, None, None),
        # change to pytest.param("postgres", "rentities", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "rentities", None, None, None),
    ],
    indirect=True,
)
def test_link_two_occ(dbsystem):
    """Test the linking of two occurrences

    Will test all the possible combinations:
        two unbound occurrences
        first one bound second unbound
        first one unboud second bound
        both bound to same real entity
        both bound to separate real entities

    Also tests deletion of real entities
    and determining the real entity of an occurrence
    """
    with dbsystem.session() as session:

        session.expire_on_commit = False

        file1 = Path(TEST_FILES_DIR, "sameas-tests.xml")
        try:
            import_from_xml(file1, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise

        ricci = session.get(Person, "deh-matteo-ricci")
        assert ricci is not None, "could not get a person from file"
        ricci.to_kleio()

        test_rid = "rp-matteo"

        REntity.delete(test_rid, session=session)

        # Fetch occurrences
        # everyboby with a name like Matteo Ricci
        occurrences = [
            id
            for (id,) in session.query(Person.id)
            .filter(Person.name.like("Mat%Ricci"))
            .all()
        ]

        # Shuffle the occurrences to randomize the order
        random.shuffle(occurrences)

        # erase any previous real entities
        # select distinct real_id from links where entity_id in (occurrences)
        stmt = select(Link.rid).where(Link.entity.in_(occurrences)).distinct()

        rids = session.execute(stmt).scalars().all()

        for real_id in rids:
            REntity.delete(real_id, session=session)
            link = session.query(Link).where(Link.rid == real_id).all()
            print(link)

        # test all the combinations
        occ1 = occurrences[0]
        occ2 = occurrences[1]
        # two unbound occurrences
        ri1 = REntity.same_as(
            occ1, occ2, real_id=test_rid, status=STATUS.MANUAL, session=session
        )
        assert ri1 is not None, "Real entity not returned"
        assert ri1.id == test_rid, "real_id not preserved"

        occ3 = occurrences[2]
        # first one bound second unbound
        ri2 = REntity.same_as(occ2, occ3, status=STATUS.AUTOMATIC, session=session)
        assert ri2.id == ri1.id
        # first one unboud second bound
        occ4 = occurrences[3]
        r3 = REntity.same_as(occ4, occ3, status=STATUS.AUTOMATIC, session=session)
        assert r3.id == ri1.id

        # both bound to same real entity
        r4 = REntity.same_as(occ4, occ3, status=STATUS.AUTOMATIC, session=session)
        assert r4.id == ri1.id

        # both bound to separate real entities
        occ5 = occurrences[4]
        occ6 = occurrences[5]
        r5 = REntity.same_as(occ5, occ6, status=STATUS.AUTOMATIC, session=session)
        assert r5.id != ri1.id
        # now merge the two real entities
        r6 = REntity.same_as(occ5, occ1, status=STATUS.AUTOMATIC, session=session)
        assert r6.id == ri1.id

        r5 = session.get(REntity, r5.id)
        assert r5 is None

        # check that the real entity has the correct number of occurrences
        rel_entity = session.get(REntity, r6.id)
        occs = [link.entity for link in rel_entity.links]
        assert len(occs) == 6
        assert occ1 in occs
        assert occ2 in occs
        assert occ3 in occs
        assert occ4 in occs
        assert occ5 in occs
        assert occ6 in occs

        # check that subsequent calls to same_as return the same real entity
        r7 = REntity.same_as(occ5, occ6, status=STATUS.AUTOMATIC, session=session)
        assert r7.id == r6.id

        # check that cannot set real_id if occurrences are already bound
        with pytest.raises(ValueError):
            REntity.same_as(
                occ5, occ6, real_id="xpto", status=STATUS.AUTOMATIC, session=session
            )

        real_ricci = session.get(REntity, ri1.id)
        assert len(real_ricci.to_kleio()) > 0
        real_ricci2 = REntity.get(ri1.id, session=session)
        assert real_ricci.id == real_ricci2.id


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", RENTITY_DB, None, None, None),
        # change to pytest.param("postgres", "rentities", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "rentities", None, None, None),
    ],
    indirect=True,
)
def test_make_real(dbsystem):
    """Test the creation of a real entity"""
    with dbsystem.session() as session:
        file1 = Path(TEST_FILES_DIR, "sameas-tests.xml")
        try:
            import_from_xml(file1, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        bento_de_gois = session.get(Person, "deh-bento-de-gois")
        assert bento_de_gois is not None, "could not get a person from file"

        rid = REntity.make_real(
            bento_de_gois.id, status=STATUS.AUTOMATIC, session=session
        )
        assert rid is not None, "real_id not returned"
        real_bento = session.get(REntity, rid.id)
        assert len(real_bento.to_kleio()) > 0


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", "xsameas", None, None, None),
        # change to pytest.param("postgres", "rentities", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "xsameas", None, None, None),
    ],
    indirect=True,
)
def test_import_xsameas(dbsystem: TimelinkDatabase):
    # Test that the sequence of import files does not affect the result
    file1 = "sameas-tests.cli"
    file2 = "xsameas-tests.cli"

    with dbsystem.session() as session:

        dbsystem.update_from_sources(file1)
        dbsystem.update_from_sources(file2)

        # check the number of KleioFiles imported
        stmt = select(KleioImportedFile)

        kfiles = session.execute(stmt).scalars().all()
        print(len(kfiles))

        # count the number of links
        stmt = select(Link)
        links = session.execute(stmt).scalars().all()
        linked_entities = sorted([link.entity for link in links])
        linked_rentities = sorted([link.rid for link in links])

        nlinks = len(links)

        # the problem here is that 'bio-michele-ruggieri-his4-19-per1-21'
        # occurs twice in the link list
        # ('rp744201',
        # 'bio-michele-ruggieri-his4-19-per1-21',
        # 'xsameas-tests')
        # this a bug in the sameas processing
        # count the number of relations with None in destination
        stmt = select(Relation).where(Relation.destination is None)
        relations = session.execute(stmt).scalars().all()
        nrelations = len(relations)

        # We now reimport file1 and check if the number of links and relations is the same
        importfile1: List[KleioFile] = dbsystem.kserver.get_translations(file1)
        xml_file = importfile1[0].xml_url
        import_from_xml(
            xml_file,
            session,
            options={
                "return_stats": True,
                "kleio_token": dbsystem.kserver.get_token(),
                "kleio_url": dbsystem.kserver.get_url(),
                "mode": "TL",
            },
        )

        stmt = select(Link)
        links2 = session.execute(stmt).scalars().all()
        linked_entities_2 = sorted([link.entity for link in links2])
        linked_rentities_2 = sorted([link.rid for link in links2])

        diff = set(linked_entities) - set(linked_entities_2)
        re_diff = set(linked_rentities) - set(linked_rentities_2)
        print(diff, re_diff)
        # this fails because the redundant link above was
        # removed in this phase.
        assert len(links) == nlinks, "wrong number of links"
        assert len(relations) == nrelations, "wrong number of relations"
        assert len(diff) == 0, "wrong number of occurrences linked"
        assert len(re_diff) == 0, "wrong number of rentities linked"

        stmt = select(Relation).where(Relation.destination == None)  # noqa
        relations2 = session.execute(stmt).scalars().all()
        assert len(relations2) == nrelations, "some relations have no destination after reimport"


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", RENTITY_DB, None, None, None),
        # change to pytest.param("postgres", "rentities", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "rentities", None, None, None),
    ],
    indirect=True,
)
def test_import_aregister(dbsystem):
    """Test the import a identifications file"""
    file = Path(TEST_FILES_DIR, "aregister-tests.xml")
    # first fill in the database with the sameas file
    file1 = "sameas-tests.cli"
    dbsystem.update_from_sources(file1)
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile = stats["file"]
        assert "aregister" in sfile.name  # ensure import was done
        real_person = session.get(REntity, "rp-66")
        assert (
            real_person is not None
        ), "could not get a real person from identifications import"  # noqa
        assert len(real_person.get_occurrences()) == 10, "wrong number of occurrences"
        kleio = real_person.to_kleio()
        assert len(kleio) > 0
        # Import again
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile = stats["file"]
        assert "aregister" in sfile.name
        real_person = session.get(REntity, "rp-66")
        assert (
            real_person is not None
        ), "could not get a real person from identifications import"
        assert len(real_person.get_occurrences()) == 10, "wrong number of occurrences"


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", RENTITY_DB, None, None, None),
        # change to pytest.param("postgres", "rentities", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "rentities", None, None, None),
    ],
    indirect=True,
)
def test_random_id(dbsystem):
    """Test the generation of a random id"""
    with dbsystem.session() as session:
        id1 = REntity.generate_id(session=session)
        id2 = REntity.generate_id(session=session)
        assert id1 != id2
