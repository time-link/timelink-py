from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class translation_status_enum(str, Enum):
    V = "V" # valid translations
    T = "T" # need translation (source more recent than translation)
    E = "E" # translation with errors
    W = "W" # translation with warnings
    P = "P" # translation being processed
    Q = "Q" # file queued for translation

class KleioFile(BaseModel):
    path: str = Field(..., description="The path of the file")
    name: str = Field(..., description="The name of the file")
    size: int = Field(..., description="The size of the file in bytes")
    directory: str = Field(..., description="The directory containing the file")
    modified: datetime = Field(..., description="The last modified time of the file")
    modified_iso: datetime = Field(..., description="The last modified time of the file in ISO format")
    modified_string: str = Field(..., description="The last modified time of the file as a string")
    qtime: datetime = Field(..., description="The time the file was queued for translation")
    qtime_string: str = Field(..., description="The time the file was queued for translation as a string")
    source_url: str = Field(..., description="The URL of the source file")
    status: translation_status_enum = Field(..., description="""The status of the file: 
                            V = valid translations
                            T = need translation (source more recent than translation)
                            E = translation with errors
                            W = translation with warnings
                            P = translation being processed
                            Q = file queued for translation""")
    translated: Optional[datetime] = Field(None, description="The time the file was translated")
    translated_string: Optional[str] = Field(None, description="The time the file was translated as a string")
    errors: Optional[int] = Field(None, description="The number of errors encountered during translation")
    warnings: Optional[int] = Field(None, description="The number of warnings encountered during translation")
    version: Optional[str] = Field(None, description="The version of the kleio translator")
    rpt_url: Optional[str] = Field(None, description="The URL of the report file")
    xml_url: Optional[str] = Field(None, description="The URL of the XML file")

class ApiPermissions(str,Enum):
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