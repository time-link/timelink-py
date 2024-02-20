from typing import Optional
from pydantic import BaseModel, AnyUrl
from timelink.kleio.kleio_server import KleioServer
from timelink.api.database import TimelinkDatabase


class Project(BaseModel):
    name: str
    DatabaseURL: Optional[AnyUrl] = None
    kleioServerURL: Optional[AnyUrl] = None
