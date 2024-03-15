from typing import Optional
from datetime import datetime
from pydantic import BaseModel as BaseModel
from pydantic import ConfigDict
from timelink.kleio.kleio_server import KleioServer  # noqa
from timelink.api.database import TimelinkDatabase  # noqa
from ..schemas import UserSchema


class ProjectAccess(BaseModel):
    id: int
    user: UserSchema
    project: "ProjectSchema"
    access_level: Optional[str] = None

    # ORM mode
    model_config = ConfigDict(from_attributes=True)


class ProjectSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    databaseURL: Optional[str] = None
    kleioServerURL: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    # ORM mode
    model_config = ConfigDict(from_attributes=True)
