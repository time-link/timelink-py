# Pydantic schema
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserPropertySchema(BaseModel):
    name: str
    value: str

    model_config = ConfigDict(from_attributes=True)


class UserProjectSchema(BaseModel):
    """ This is used to avoid circular import between UserSchema and ProjectSchema."""
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
    - fullname: Optional[str]
    - email: str
    - nickname: Optional[str]
    - disabled: Optional[bool]
    - properties: Optional[List[UserPropertySchema]]"""
    name: str
    fullname: Optional[str]
    email: str
    nickname: Optional[str]
    disabled: Optional[bool]
    properties: Optional[List[UserPropertySchema]]
    projects: Optional[List["UserProjectSchema"]]  # noqa Flake8: F821
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    # ORM mode
    model_config = ConfigDict(from_attributes=True)
