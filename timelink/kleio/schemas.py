# flake8: noqa: E741
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class translation_status_enum(str, Enum):
    V = "V"  # valid translations
    T = "T"  # need translation (source more recent than translation)
    E = "E"  # translation with errors
    W = "W"  # translation with warnings
    P = "P"  # translation being processed
    Q = "Q"  # file queued for translation


class import_status_enum(str, Enum):
    I = "I"  # imported
    E = "E"  # imported with error
    W = "W"  # imported with warnings no errors
    N = "N"  # not imported
    U = "U"  # translation updated need to reimport


class KleioFile(BaseModel):
    """Represents the information about a kleio file and its
    translation and import status"""

    path: str = Field(..., description="The path of the file")
    name: str = Field(..., description="The name of the file")
    size: int = Field(..., description="The size of the file in bytes")
    directory: str = Field(..., description="The directory containing the file")
    modified: datetime = Field(..., description="The last modified time of the file")
    modified_iso: datetime = Field(
        ..., description="The last modified time of the file in ISO format"
    )
    modified_string: str = Field(
        ..., description="The last modified time of the file as a string"
    )
    qtime: datetime = Field(
        ..., description="The time the file was queued for translation"
    )
    qtime_string: str = Field(
        ..., description="The time the file was queued for translation as a string"
    )
    source_url: str = Field(..., description="The URL of the source file")
    """The status of the file:
        .. code-block:: python

            V = "valid translations"
            T = "need translation (source more recent than translation)"
            E = "translation with errors"
            W = "translation with warnings"
            P = "translation being processed"
            Q = "file queued for translation"
    """
    status: translation_status_enum = Field(
        ...,
        description="""The status of the file:
                            V = valid translations
                            T = need translation (source more recent than translation)
                            E = translation with errors
                            W = translation with warnings
                            P = translation being processed
                            Q = file queued for translation""",
    )
    translated: Optional[datetime] = Field(
        None, description="The time the file was translated"
    )
    translated_string: Optional[str] = Field(
        None, description="The time the file was translated as a string"
    )
    errors: Optional[int] = Field(
        None, description="The number of errors encountered during translation"
    )
    warnings: Optional[int] = Field(
        None, description="The number of warnings encountered during translation"
    )
    version: Optional[str] = Field(
        None, description="The version of the kleio translator"
    )
    rpt_url: Optional[str] = Field(None, description="The URL of the report file")
    xml_url: Optional[str] = Field(None, description="The URL of the XML file")
    import_status: Optional[import_status_enum] = Field(
        None,
        description="""The status of the file import:
                            I = imported
                            E = imported with error
                            W = imported with warnings no errors
                            N = not imported
                            U = translation updated need to reimport""",
    )
    import_errors: Optional[int] = Field(
        None, description="The number of errors encountered during import"
    )
    import_warnings: Optional[int] = Field(
        None, description="The number of warnings encountered during import"
    )
    import_error_rpt: Optional[str] = Field(
        None, description="Error report from import"
    )
    import_warning_rpt: Optional[str] = Field(
        None, description="Warning report from import"
    )
    imported: Optional[datetime] = Field(None, description="Date of import of the file")
    imported_string: Optional[str] = Field(
        None, description="Date of import of the file as a string"
    )

    def needs_translation(self):
        """Return True if the file needs translation"""
        return self.status == translation_status_enum.T

    def needs_import(self):
        """Return True if the file needs import

        A file needs import if it has not been imported before
            or if it has been translated again since the last import
        """
        if self.import_status is None:
            raise ValueError(
                "import_status is None. Call TimelinkDatabase.get_import_status() first."
            )

        return (
            self.import_status == import_status_enum.N
            or self.import_status == import_status_enum.U
        )


class ApiPermissions(str, Enum):
    sources = "sources"
    kleioset = "kleioset"
    files = "files"
    structures = "structures"
    translations = "translations"
    upload = "upload"
    delete = "delete"
    mkdir = "mkdir"
    rmdir = "rmdir"


"""
        info = {
            "comment": "An user able to translate, upload and delete files, and also create and remove directories, in specific sub-directoris in kleio-home",
            "api": [
                "sources",
                "kleioset",
                "files",
                "structures",
                "translations",
                "upload",
                "delete",
                "mkdir",
                "rmdir"
                ],
            "structures": "structures/reference_sources",
            "sources": "sources/reference_sources"
        }
"""


class TokenInfo(BaseModel):
    comment: str = Field(..., description="Comment")
    api: list[ApiPermissions] = Field(..., description="API permissions")
    structures: str = Field(..., description="Structures")
    sources: str = Field(..., description="Sources")
