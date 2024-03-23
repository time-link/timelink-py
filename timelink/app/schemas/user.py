# Pydantic schema
from typing import Annotated, List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, SkipValidation

from timelink.api.database import TimelinkDatabase
from timelink.kleio.kleio_server import KleioServer


class UserPropertySchema(BaseModel):
    name: str
    value: str

    model_config = ConfigDict(from_attributes=True)


class UserProjectSchema(BaseModel):

    user_id: Optional[int] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    project_description: Optional[str] = None
    access_level: Optional[str] = None

    # ORM mode
    model_config = ConfigDict(from_attributes=True)


class UserSchema(BaseModel):
    """User schema.

    Fields:
    - name: str
    - email: str
    - nickname: Optional[str]
    - disabled: Optional[bool]
    - properties: Optional[List[UserPropertySchema]]"""
    name: str
    email: str
    nickname: Optional[str]
    disabled: Optional[bool]
    properties: Optional[List[UserPropertySchema]]
    projects: Optional[List["UserProjectSchema"]]  # noqa Flake8: F821
    current_project_name: Optional[str] = None
    current_project_db: Annotated[TimelinkDatabase, SkipValidation] = None
    current_project_kleio_server: Annotated[KleioServer, SkipValidation] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def is_admin(self, admin_property: str = "permission:timelink:admin"):
        for prop in self.properties:
            if prop.name == admin_property and prop.value in ["true", "yes"]:
                return True
        return False

    # ORM mode
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
