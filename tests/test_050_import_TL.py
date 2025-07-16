"""Test the import of Kleio files into the Timelink database.
Check tests.__init__.py for parameters

"""
# pylint: disable=import-error
import logging
import os
from pathlib import Path
from time import sleep

import pytest

from tests import TEST_DIR, get_one_translation, skip_on_travis, has_internet
from timelink.api.models.system import KleioImportedFile
from timelink.kleio.importer import import_from_xml
from timelink.api.models import base  # pylint: disable=unused-import. # noqa: F401
from timelink.api.models.base import Person, PomSomMapper
from timelink.api.database import (
    TimelinkDatabase,
    get_import_status,
)
from timelink.api.models.entity import Entity

from timelink.kleio.kleio_server import KleioServer
from timelink.kleio.schemas import KleioFile

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis

TEST_DB = "test_import_tl"
db_path = f"{TEST_DIR}/sqlite/"
test_set = [("sqlite", TEST_DB), ("postgres", TEST_DB)]


@pytest.fixture(scope="module")
def dbsystem(request, kleio_server):
    """Create a database for testing"""
    db_type, db_name = request.param
    # only used for sqlite databases

    database = TimelinkDatabase(db_name, db_type, db_path=db_path,
                                echo=False,
                                kleio_server=kleio_server)
    try:

        yield database
    finally:
        database.drop_db()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_xml(dbsystem):
    """Test the import of a Kleio file into the Timelink database"""
    file: Path = Path(TEST_DIR, "xml_data/b1685.xml")
    with dbsystem.session() as session:

        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            session.rolback()
            raise
        sfile: Path = stats["file"]
        assert sfile.name == file.name
        domingos_vargas = session.get(Person, "b1685.33-per6")
        assert domingos_vargas is not None, "could not get a person from file"
        kleio = domingos_vargas.to_kleio()
        assert len(kleio) > 0


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_linked_data_attributes(dbsystem):
    """Test the import of a translation with linked_data in attributes"""
    path = "projects/test-project/sources/reference_sources/linked_data"
    dbsystem.update_from_sources(path=path)
    with dbsystem.session() as session:
        try:
            per: Person = session.get(Person, "deh-antonio-de-abreu")
            assert per is not None, "could not get a group with linked data from file"
            k = per.to_kleio()
            print(k)
            # check for attributes with extra_info
            for a in per.attributes:
                if len(a.extra_info) > 0:
                    assert a.extra_info.keys is not None
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_linked_data_geoentites(dbsystem):
    """Test the import of a translation with linked_data"""
    file: Path = Path(TEST_DIR, "xml_data/dehergne-locations-1644.xml")
    with dbsystem.session() as session:

        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            session.rollback()
            raise
        sfile: Path = stats["file"]
        assert sfile.name == file.name
        geo1 = session.get(Entity, "deh-r1644-chekiang")
        assert geo1 is not None, "could not get a group with linked data from file"
        assert geo1.get_extra_info() is not None


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_atr_date(dbsystem):
    """Test the import of a Kleio file with explicit attribute dates"""
    file: Path = Path("projects/test-project/sources/reference_sources/test-attr-dates/test-attr-dates.cli")
    dbsystem.update_from_sources(file)
    with dbsystem.session() as session:
        try:
            domingos_vargas = session.get(Person, "t140337")
            assert domingos_vargas is not None, "could not get a person from file"
            kleio = domingos_vargas.to_kleio()
            assert len(kleio) > 0
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_with_custom_mapping(dbsystem):
    """Test the import of a Kleio file into the Timelink database with a custom mapping"""
    file = Path("projects/test-project/sources/reference_sources/devassas/dev1692.cli")
    dbsystem.update_from_sources(file)
    with dbsystem.session() as session:
        try:
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
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_issue48(dbsystem):
    """ Problem with importing mapping hierarchies issue #48 """
    path = "projects/test-project/sources/reference_sources/issues/issue48/"
    dbsystem.update_from_sources(path=path)
    with dbsystem.session() as session:
        try:
            carta = session.get(Entity, "deh-ca-1645-b-2-a")
            assert carta.the_type is not None, "carta did not have a type"
            pom_class: PomSomMapper = PomSomMapper.get_pom_class(carta.pom_class, session)
            assert pom_class.element_class_to_column('type', session) is not None
            crono = session.get(Entity, "issue48-sourceb-his1-79")
            assert crono.loc is not None, "crono did not have a loc"
            pom_class: PomSomMapper = PomSomMapper.get_pom_class(crono.pom_class, session)
            assert pom_class.element_class_to_column('loc', session) is not None
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_with_many(dbsystem):
    """Test the import of a long Kleio file into the Timelink database"""
    file = Path("projects/test-project/sources/reference_sources/varia/auc-alunos.cli")
    dbsystem.update_from_sources(file)
    with dbsystem.session() as session:
        try:
            estudante = session.get(Entity, "140771")
            kleio = estudante.to_kleio()
            assert len(kleio) > 0
            assert estudante is not None, (
                "could not get an entity from big import"
            )  # noqa
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.skipif(not has_internet(), reason="No internet connection available")
@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_git_hub(dbsystem):
    """Test the import of a Kleio file from github into the Timelink database"""
    file = "https://raw.githubusercontent.com/time-link/timelink-py/f76007cb7b98b39b22be8b70b3b2a62e7ae0c12f/tests/xml_data/b1685.xml"  # noqa
    with dbsystem.session() as session:
        try:
            stats = import_from_xml(file, session, options={"return_stats": True})
        except Exception as exc:
            print(exc)
            session.rollback()
            raise
        try:
            domingos_vargas = session.get(Person, "b1685.33-per6")
            assert domingos_vargas is not None, "could not get a person from file"
            kleio = domingos_vargas.to_kleio()
            assert len(kleio) > 0
            sfile: Path = stats["file"]
            assert "b1685.xml" in sfile
        except Exception as exc:
            print(exc)
            session.rollback()
            raise
        pass


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_from_kleio_server(dbsystem, kleio_server):
    """Test the import of a Kleio file from kleio server into the Timelink database"""
    kserver: KleioServer = kleio_server
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
    # select a file randomly
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
            session.rollback()

        try:
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
        except Exception as exc:
            print(exc)
            session.rollback()
            raise


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_import_status_1(dbsystem, kleio_server):
    """Test if import status is retrieved"""
    kserver: KleioServer = kleio_server
    kleio_file = get_one_translation(kserver)
    translations = [kleio_file]
    assert len(translations) > 0, "no valid translations found in Kleio Server"
    import_status = get_import_status(dbsystem, translations, match_path=True)
    assert import_status is not None
