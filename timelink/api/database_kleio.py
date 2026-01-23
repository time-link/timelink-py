"""Database Kleio Mixin for Timelink.

This module provides the DatabaseKleioMixin class, which contains methods for
integrating a Timelink database with a Kleio server. It handles file imports,
translation tracking, and synchronization between source files and the database.
"""

import logging
import time
from typing import List

from pydantic import TypeAdapter

from timelink.api.models import KleioImportedFile
from timelink.api.models.system import KleioImportedFileSchema
from timelink.kleio import KleioFile, KleioServer, import_status_enum
from timelink.kleio.importer import import_from_xml

from .database_utils import get_import_status


class DatabaseKleioMixin:
    """Methods for interaction with Kleio Server and file imports.

    This mixin provides high-level operations for importing data from Kleio sources,
    checking import status, and managing translations through an attached Kleio server.
    """

    def set_kleio_server(self, kleio_server: KleioServer):
        """Set the kleio server for imports

        Args:
            kleio_server (KleioServer): kleio server
        """
        self.kserver = kleio_server

    def get_kleio_server(self):
        """Return the kleio server associated with this database"""
        return self.kserver

    def get_imported_files(self) -> List[KleioImportedFileSchema]:
        """Return the list of previously imported Kleio files in the database.

        Returns:
            List[KleioImportedFileSchema]: List of imported file records with metadata.
        """
        with self.session() as session:
            result = session.query(KleioImportedFile).all()
            # Convert to Pydantic Schema
            ta = TypeAdapter(List[KleioImportedFileSchema])
            result_pydantic = ta.validate_python(result)
        return result_pydantic

    def get_import_status(
        self,
        kleio_files: List[KleioFile] = None,
        path=None,
        recurse=True,
        status=None,
        match_path=False,
    ) -> List[KleioFile]:
        """Get the import status of Kleio files.

        Retrieves import status information stored in the database for the provided
        Kleio files. If no files are provided, fetches translations from the attached
        Kleio server.

        Args:
            kleio_files (List[KleioFile], optional): List of Kleio files to check.
                If None, files are retrieved from the attached Kleio server. Defaults to None.
            path (str, optional): Path to search for sources on the Kleio server. Defaults to None.
            recurse (bool, optional): If True, recursively search subdirectories. Defaults to True.
            status (import_status_enum, optional): Filter results by import status. Defaults to None.
            match_path (bool, optional): If True, match files by full path instead of just filename.
                Defaults to False.

        Returns:
            List[KleioFile]: List of Kleio files with updated import_status attributes.

        Raises:
            ValueError: If kleio_files is empty and no Kleio server is attached, or if
                kleio_files is not a list of KleioFile objects.

        See Also:
            :func:`timelink.api.database_utils.get_import_status` for details on status values.
        """
        if kleio_files is None:
            if self.get_kleio_server() is None:
                raise ValueError(
                    "Empty list of files. \n" "Either provide list of files or attach database to Kleio server."
                )
            else:
                kleio_files = self.get_kleio_server().get_translations(path=path, recurse=recurse)
        if isinstance(kleio_files, KleioFile):
            kleio_files = [kleio_files]
        if not isinstance(kleio_files, list) or not all(isinstance(file, KleioFile) for file in kleio_files):
            raise ValueError(
                f"kleio_files must be a list of KleioFile objects."
                f"Use path={kleio_files} to get a list of KleioFile objects from a Kleio server."
            )

        files: List[KleioFile] = get_import_status(self, kleio_files=kleio_files, match_path=match_path)
        if status is not None:
            # Allow status to be either an import_status_enum or a raw string code.
            status_value = status.value if isinstance(status, import_status_enum) else status
            files = [file for file in files if file.import_status.value == status_value]
        return files

    def get_need_import(
        self,
        kleio_files: List[KleioFile] = None,
        with_import_errors=False,
        with_import_warnings=False,
        match_path=False,
    ) -> List[KleioFile]:
        """Identify Kleio files that require importing into the database.

        Files are considered needing import if they have never been imported (status N)
        or if they have been updated since the last import (status U). Optionally,
        files with previous import errors or warnings can be included.

        Args:
            kleio_files (List[KleioFile], optional): List of Kleio files to check.
                If None, files are retrieved via the attached Kleio server.
            with_import_errors (bool, optional): If True, include files that were
                previously imported but had errors (status E). Defaults to False.
            with_import_warnings (bool, optional): If True, include files that were
                previously imported but had warnings (status W). Defaults to False.
            match_path (bool, optional): If True, match files by full path instead
                of just filename. Defaults to False.

        Returns:
            List[KleioFile]: List of Kleio files that require importing.
        """

        kleio_files: List[KleioFile] = self.get_import_status(kleio_files, match_path=match_path)
        return [
            file
            for file in kleio_files
            if (file.import_status == import_status_enum.N or file.import_status == import_status_enum.U)
            or (with_import_errors and file.import_status == import_status_enum.E)
            or (with_import_warnings and file.import_status == import_status_enum.W)
        ]

    def get_import_rpt(self, path: str, match_path=False) -> str:
        """Retrieve the import report for a specific file from the database.

        Concatenates error and warning reports for the specified file.

        Args:
            path (str): The filename or full path of the file.
            match_path (bool, optional): If True, match by the full path stored
                in the database. If False, match by filename only. Defaults to False.

        Returns:
            str: A string containing the concatenated error and warning reports,
                 or "No import report found" if the file record does not exist.
        """
        with self.session() as session:
            if match_path:
                result = session.query(KleioImportedFile).filter(KleioImportedFile.path == path).first()
            else:
                result = session.query(KleioImportedFile).filter(KleioImportedFile.name == path).first()
            if result is not None:
                s = result.error_rpt + "\n" + result.warning_rpt
            else:
                s = "No import report found"
        return s

    def update_from_sources(
        self,
        path=None,
        recurse=True,
        with_translation_warnings=True,
        with_translation_errors=False,
        with_import_errors=False,
        with_import_warnings=False,
        force=False,
        match_path=False,
    ):
        """Synchronize the database with source files using an attached Kleio server.

        This method coordinates the end-to-end update process:
        1. Identifies files that need translation on the Kleio server.
        2. Requests translations and waits for them to complete.
        3. Identifies files that need to be imported into the database (New or Updated).
        4. Imports the resulting XML data into the database.

        Args:
            path (str, optional): Base path for sources. If None, all sources are checked.
            recurse (bool, optional): If True, recursively search subdirectories. Defaults to True.
            with_translation_warnings (bool, optional): If True, include files that translated
                with warnings. Defaults to True.
            with_translation_errors (bool, optional): If True, include files that translated
                with errors. Defaults to False.
            with_import_errors (bool, optional): If True, re-import files that previously
                had import errors. Defaults to False.
            with_import_warnings (bool, optional): If True, re-import files that previously
                had import warnings. Defaults to False.
            force (bool, optional): If True, force translation and import regardless of
                current status. Defaults to False.
            match_path (bool, optional): If True, match files by full path instead of
                just filename. Defaults to False.

        Raises:
            ValueError: If no Kleio server is attached to the database.
        """
        logging.debug("Updating from sources")
        if self.kserver is None:
            raise ValueError("No kleio server attached to this database")
        else:
            if path is None:
                path = ""
                logging.debug("Path set to ''")

            if force:
                translate_status = None  # this gets all files, no matter status
            else:
                translate_status = "T"  # only those that need translation

            for kfile in self.kserver.get_translations(path=path, recurse=recurse, status=translate_status):
                logging.info("Request translation of %s %s", kfile.status.value, kfile.path)
                self.kserver.translate(kfile.path, recurse="no", spawn="no")
            # wait for translation to finish
            logging.debug("Waiting for translations to finish")
            pfiles = self.kserver.get_translations(path=path, recurse="yes", status="P")

            qfiles = self.kserver.get_translations(path=path, recurse="yes", status="Q")
            # TODO: change to import as each translation finishes
            while len(pfiles) > 0 or len(qfiles) > 0:
                time.sleep(1)

                pfiles = self.kserver.get_translations(path="", recurse="yes", status="P")
                qfiles = self.kserver.get_translations(path="", recurse="yes", status="Q")
            # import the files
            to_import = self.kserver.get_translations(path=path, recurse=recurse, status="V")  # TODO recurse make param
            if with_translation_warnings:
                to_import += self.kserver.get_translations(path=path, recurse=recurse, status="W")
            if with_translation_errors:
                to_import += self.kserver.get_translations(path=path, recurse=recurse, status="E")

            if force:
                import_needed = to_import
            else:
                import_needed = self.get_need_import(
                    to_import,
                    with_import_errors,
                    with_import_warnings,
                    match_path=match_path,
                )

            for kfile in import_needed:
                kfile: KleioFile
                with self.session() as session:
                    try:
                        logging.info("Importing %s", kfile.path)
                        stats = import_from_xml(
                            kfile.xml_url,
                            session=session,
                            options={
                                "return_stats": True,
                                "kleio_token": self.kserver.get_token(),
                                "kleio_url": self.kserver.get_url(),
                                "mode": "TL",
                            },
                        )
                        logging.debug("Imported %s: %s", kfile.path, stats)
                        time.sleep(1)
                    except Exception as e:
                        session.rollback()
                        logging.error("Unexpected error:")
                        logging.error("Error: %s", e)
                        continue

    def import_from_xml(self, file: str | KleioFile, kserver=None, return_stats=True):
        """Import one file

        Args:
           file (str | KleioFile): path to xml file or KleioFile object
            kserver (KleioServer, optional): Kleio server to use for import. Defaults to None.
            return_stats (bool, optional): Return import stats. Defaults to True.
        """
        if isinstance(file, KleioFile):
            path = file.xml_url
        else:
            path = file

        if kserver is None:
            kserver = self.kserver
        if kserver is None:
            raise ValueError("No kleio server attached to this database. Attach kleio server or provide one in call.")
        # TODO: #18 expose import_from_xml in TimelinkDatabase
        stats = None
        with self.session() as session:
            try:
                stats = import_from_xml(
                    path,
                    session=session,
                    options={
                        "return_stats": return_stats,
                        "kleio_token": kserver.get_token(),
                        "kleio_url": kserver.get_url(),
                        "mode": "TL",
                    },
                )
            except Exception as e:
                session.rollback()
                logging.error(f"Error importing XML: {e}")
        return stats
