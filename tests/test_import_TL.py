"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""
# pylint: disable=import-error
import logging
import os
from pathlib import Path
from time import sleep

import pytest

from tests import TEST_DIR, get_one_translation, skip_on_travis
from timelink.api.models.system import KleioImportedFile
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person
from timelink.api.database import (
    TimelinkDatabase,
    start_postgres_server,
    get_postgres_container_user,
    get_postgres_container_pwd,
    get_import_status,
)
from timelink.api.models.entity import Entity

from timelink.kleio import KleioServer
from timelink.kleio.schemas import KleioFile

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name, db_url, db_user, db_pwd = request.param
    if db_type == "postgres":
        start_postgres_server()
        db_user = get_postgres_container_user()
        db_pwd = get_postgres_container_pwd()

    database = TimelinkDatabase(db_name, db_type, db_url, db_user, db_pwd)
    try:
        yield database
    finally:
        # database.drop_db
        database.session().close()


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        # change to pytest.param("postgres", "tests", None, None, None, marks=skip_on_travis)
        # to skip the test on travis see https://doc.pytest.org/en/latest/how-to/skipping.html#skip-xfail-with-parametrize
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_xml(dbsystem):
    """Test the import of a Kleio file into the Timelink database"""
    file: Path = Path(TEST_DIR, "xml_data/b1685.xml")
    session = dbsystem.session()
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    domingos_vargas = session.get(Person, "b1685.33-per6")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_linked_data_attributes(dbsystem):
    """Test the import of a translation with linked_data in attributes"""
    file: Path = Path(TEST_DIR, "xml_data/dehergne-a.xml")
    session = dbsystem.session()
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    per: Person = session.get(Person, "deh-antonio-de-abreu")
    assert per is not None, "could not get a group with linked data from file"
    # check for attributes with extra_info
    for a in per.attributes:
        if 'extra_info' in a.obs:
            assert a.get_extra_info() is not None


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_linked_data_geoentites(dbsystem):
    """Test the import of a translation with linked_data"""
    file: Path = Path(TEST_DIR, "xml_data/dehergne-locations-1644.xml")
    session = dbsystem.session()
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    geo1 = session.get(Entity, "deh-r1644-chekiang")
    assert geo1 is not None, "could not get a group with linked data from file"
    assert geo1.get_extra_info() is not None


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_atr_date(dbsystem):
    """Test the import of a Kleio file with explicit attribute dates"""
    file: Path = Path(TEST_DIR, "xml_data/test-atr-date.xml")
    session = dbsystem.session()
    try:
        stats = import_from_xml(file, session, options={"return_stats": True})
    except Exception as exc:
        print(exc)
        raise
    sfile: Path = stats["file"]
    assert sfile.name == file.name
    domingos_vargas = session.get(Person, "t140337")
    assert domingos_vargas is not None, "could not get a person from file"
    kleio = domingos_vargas.to_kleio()
    assert len(kleio) > 0


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_with_custom_mapping(dbsystem):
    """Test the import of a Kleio file into the Timelink database with a custom mapping"""
    file = Path(TEST_DIR, "xml_data/dev1692.xml")
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile = stats["file"]
        assert "dev1692" in sfile.name
        caso = session.get(Entity, "c1692-antonio-cordeiro-alcouc")
        caso_kleio = caso.to_kleio()
        assert len(caso_kleio) > 0
        assert caso is not None, "could not get an entity from special mapping"
        caso_kleio = caso.to_kleio()
        assert len(caso_kleio) > 0
        test = session.get(Entity, "dev1692-per5")
        assert test is not None
        test_kleio = test.to_kleio()
        assert len(test_kleio) > 0


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_with_many(dbsystem):
    """Test the import of a long Kleio file into the Timelink database"""
    file = Path(TEST_DIR, "xml_data/test-auc-alunos-264605-A-140337-140771.xml")
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile = stats["file"]
        assert "alunos" in sfile.name
        estudante = session.get(Entity, "140771")
        kleio = estudante.to_kleio()
        assert len(kleio) > 0
        assert estudante is not None, (
            "could not get an entity from big import"
        )  # noqa


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_identifications(dbsystem):
    """Test the import a identifications file"""
    file = Path(TEST_DIR, "xml_data/mhk_identification_toliveira.xml")
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        sfile = stats["file"]
        assert "identification" in sfile.name
        real_person = session.get(Entity, "rp-46")
        kleio = real_person.to_kleio()
        assert len(kleio) > 0
        assert real_person is not None, (
            "could not get a real person from identifications import"
        )  # noqa


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_git_hub(dbsystem):
    """Test the import of a Kleio file from github into the Timelink database"""
    file = "https://raw.githubusercontent.com/time-link/timelink-py/f76007cb7b98b39b22be8b70b3b2a62e7ae0c12f/tests/xml_data/b1685.xml"  # noqa
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            raise
        domingos_vargas = session.get(Person, "b1685.33-per6")
        assert domingos_vargas is not None, "could not get a person from file"
        kleio = domingos_vargas.to_kleio()
        assert len(kleio) > 0
        sfile: Path = stats["file"]
        assert "b1685.xml" in sfile
        pass


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_from_kleio_server(dbsystem):
    """Test the import of a Kleio file from kleio server into the Timelink database"""
    kserver: KleioServer = KleioServer.start(kleio_home=f"{TEST_DIR}/timelink-home",
                                             reuse=True,
                                             update=False)
    kleio_url = kserver.get_url()
    kleio_token = kserver.get_token()
    # wait for the server to start
    server_up = False
    counter = 0
    while not server_up and counter < 10:
        try:
            kserver.get_home_page()
            server_up = True
        except Exception as exc:
            logging.debug(exc)
            sleep(1)
            counter += 1
            pass
    kleio_file: KleioFile = get_one_translation(kserver)
    file = kleio_file.xml_url
    with dbsystem.session() as session:
        try:
            import_from_xml(
                file,
                session,
                options={
                    "return_stats": True,
                    "kleio_token": kleio_token,
                    "kleio_url": kleio_url,
                    "mode": "TL",
                },
            )
        except Exception as exc:
            print(exc)

        # check if the file was imported
        filename_with_extension = os.path.basename(file)
        filename, extension = os.path.splitext(filename_with_extension)
        sources = session.query(KleioImportedFile).all()
        imported = False
        for source in sources:
            kfilename_with_extension = os.path.basename(source.path)
            kfile, kextention = os.path.splitext(kfilename_with_extension)
            if kfile == filename:
                imported = True
                break

        assert imported, "file not imported"


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_status_1(dbsystem):
    """Test if import status is retrieved"""
    kserver: KleioServer = KleioServer.start(kleio_home=f"{TEST_DIR}/timelink-home",
                                             reuse=True,
                                             update=False)
    kleio_file = get_one_translation(kserver)
    translations = [kleio_file]
    assert len(translations) > 0, "no valid translations found in Kleio Server"
    import_status = get_import_status(dbsystem, translations, match_path=True)
    assert import_status is not None


@pytest.mark.parametrize(
    "dbsystem",
    [
        # db_type, db_name, db_url, db_user, db_pwd
        ("sqlite", ":memory:", None, None, None),
        ("postgres", "tests", None, None, None),
    ],
    indirect=True,
)
def test_import_sources_with_no_year(dbsystem):
    """Test the import of a Kleio file from kleio server into the Timelink database"""
    kserver: KleioServer = KleioServer.start(kleio_home=f"{TEST_DIR}/timelink-home")
    kleio_url = kserver.get_url()
    kleio_token = kserver.get_token()
    kleio_file: KleioFile = get_one_translation(kserver, path="")
    file = kleio_file.xml_url
    # file: KleioFile
    # temp = [
    #   kfile.xml_url
    #    for kfile in translations
    #   if kfile.name == "auc-alunos.cli"
    # ]
    # file = temp[0]
    with dbsystem.session() as session:
        try:
            import_from_xml(
                file,
                session,
                options={
                    "return_stats": True,
                    "kleio_token": kleio_token,
                    "kleio_url": kleio_url,
                    "mode": "TL",
                },
            )
        except Exception as exc:
            print(exc)

        # check if the file was imported
        filename_with_extension = os.path.basename(file)
        filename, extension = os.path.splitext(filename_with_extension)
        sources = session.query(KleioImportedFile).filter_by().all()
        imported = False
        for source in sources:
            kfilename_with_extension = os.path.basename(source.path)
            kfile, kextention = os.path.splitext(kfilename_with_extension)
            if kfile == filename:
                imported = True
                break

        assert imported, "file not imported"
