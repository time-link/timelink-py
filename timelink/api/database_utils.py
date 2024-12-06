"""This module provides utility functions for interacting with the Timelink database,
including generating random passwords, retrieving database passwords from the environment,
and determining the import status of Kleio files.

Functions:
    random_password() -> str:
        Generate a random password consisting of 10 ASCII letters.

    get_db_password() -> str:
        Retrieve the database password from the environment. If not set, generate a new one,
        set it in the environment, and return it.

    get_import_status(db: TimelinkDatabase, kleio_files: List[KleioFile], match_path=False) -> List[KleioFile]:
        Determine the import status of the provided Kleio files by comparing them with previously
        imported files in the database. Optionally match files by their path instead of their name.

"""
from __future__ import annotations
from datetime import timezone
import os
import random
import string
from typing import List, TYPE_CHECKING

from timelink.api.models.system import KleioImportedFileSchema
from timelink.kleio import KleioFile, import_status_enum

if TYPE_CHECKING:
    from timelink.api.database import TimelinkDatabase


def random_password():
    """Generate a random password"""

    letters = string.ascii_letters
    result_str = "".join(random.choice(letters) for i in range(10))
    return result_str


def get_db_password():
    """Get the database password from the environment.
    If none generated one and set it in the environment."""
    # get password from environment
    db_password = os.environ.get("TIMELINK_DB_PASSWORD")
    if db_password is None:
        db_password = random_password()
        os.environ["TIMELINK_DB_PASSWORD"] = db_password
    return db_password


def get_import_status(
    db: TimelinkDatabase, kleio_files: List[KleioFile], match_path=False
) -> List[KleioFile]:
    """Get the import status of the kleio files.

        The status in returned
        in :attr:`timelink.api.models.system.KleioImportedFileSchema.import_status`

    Args:
        db (TimelinkDatabase): timelink database
        kleio_files (List[KleioFile]): list of kleio files with extra field import_status
        match_path (bool, optional): if True, match the path of the kleio file
                                    with the path of the imported file;
                                    defaults to False.

    Returns:
        List[KleioFile]: list of kleio files with field import_status

    TODO: KleioFile should also receive the import_errors and import_warnings
    """

    previous_imports: List[KleioImportedFileSchema] = db.get_imported_files()
    if match_path:
        imported_files_dict = {imported.path: imported for imported in previous_imports}
        valid_files_dict = {file.path: file for file in kleio_files}
    else:
        imported_files_dict = {imported.name: imported for imported in previous_imports}
        valid_files_dict = {file.name: file for file in kleio_files}
        if len(valid_files_dict) != len(kleio_files):
            raise ValueError(
                "Some kleio files have the same name. "
                "Use match_path=True to match the full path of the kleio file "
                "with the path of the imported file."
            )

    for path, file in valid_files_dict.items():
        if (
            path not in imported_files_dict
            or file.translated is None  # noqa: W503
        ):
            file.import_status = import_status_enum.N
        elif imported_files_dict[path].imported is None:
            # if a reimport of a previous imported file fails its
            # imported date will be None and it needs reimport
            file.import_status = import_status_enum.N
        elif file.translated > imported_files_dict[path].imported.replace(
            tzinfo=timezone.utc
        ):
            file.import_status = import_status_enum.U
        else:
            file.import_errors = imported_files_dict[path].nerrors
            file.import_warnings = imported_files_dict[path].nwarnings
            file.import_error_rpt = imported_files_dict[path].error_rpt
            file.import_warning_rpt = imported_files_dict[path].warning_rpt
            file.imported = imported_files_dict[path].imported
            file.imported_string = imported_files_dict[path].imported_string
            if imported_files_dict[path].nerrors > 0:
                file.import_status = import_status_enum.E
            elif imported_files_dict[path].nwarnings > 0:
                file.import_status = import_status_enum.W
            else:
                file.import_status = import_status_enum.I
    return kleio_files
