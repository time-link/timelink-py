# Pydantic models for Kleio server API
# These represent information on translations and
# And git status

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class KleioFile(BaseModel):
    path: str
    name: str
    size: int
    directory: str
    modified: datetime
    modified_iso: datetime
    modified_string: str
    qtime: datetime
    qtime_string: str
    source_url: str
    status: str
    translated: Optional[datetime] = None
    translated_string: Optional[str] = None
    errors: Optional[int] = None
    warnings: Optional[int] = None
    version: Optional[str] = None
    rpt_url: Optional[str] = None
    xml_url: Optional[str] = None