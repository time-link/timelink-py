# Pydantic schema
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class UserProperty(BaseModel):
    property: str
    value: str

    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    name: str
    fullname: Optional[str]
    email: str
    nickname: Optional[str]
    disabled: Optional[bool]
    hashed_password: Optional[str]
    properties: Optional[List[UserProperty]]

    # ORM mode
    model_config = ConfigDict(from_attributes=True)
