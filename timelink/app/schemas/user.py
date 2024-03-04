# Pydantic schema
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class UserPropertySchema(BaseModel):
    name: str
    value: str

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

    # ORM mode
    model_config = ConfigDict(from_attributes=True)
