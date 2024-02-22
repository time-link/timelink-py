from typing import Optional
from pydantic import BaseModel, AnyUrl
from timelink.kleio.kleio_server import KleioServer  # noqa
from timelink.api.database import TimelinkDatabase  # noqa


class Project(BaseModel):
    name: str
    databaseURL: Optional[AnyUrl] = None
    kleioServerURL: Optional[AnyUrl] = None
