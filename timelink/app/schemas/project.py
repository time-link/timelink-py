from typing import Optional
from pydantic import BaseModel, AnyUrl
from timelink.kleio.kleio_server import KleioServer  # noqa
from timelink.api.database import TimelinkDatabase  # noqa
from .user import UserSchema


class ProjectAccess(BaseModel):
    id: int
    user: UserSchema
    project: "ProjectSchema"
    access_level: Optional[str] = None


class ProjectSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    databaseURL: Optional[AnyUrl] = None
    kleioServerURL: Optional[AnyUrl] = None
    created: Optional[str] = None
    updated: Optional[str] = None
