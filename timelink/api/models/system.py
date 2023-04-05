""" Models for system tables

Tables defined here:

    - syspar: system parameters
    - syslog: system log


"""

from typing import List
from enum import Enum
from datetime import date, datetime
from pydantic import BaseModel # pylint: disable=import-error

from sqlalchemy import Column, String, Integer, DateTime # pylint: disable=import-error
from sqlalchemy.sql import func # pylint: disable=import-error
from .base_class import Base

class SysPar(Base):
    """System parameters table"""
    __tablename__ = "syspar"
    pname = Column(String, primary_key=True, index=True)
    pvalue = Column(String)
    ptype = Column(String)
    obs = Column(String)

class SysLog(Base):
    """System log table"""
    seq = Column(Integer, primary_key=True, index=True, autoincrement=True)
    time = Column(DateTime, default=func.now())
    level = Column(Integer)
    origin = Column(String)
    message = Column(String)

class ParTypeSchema(str,Enum):

    """Parameter type

    Fields:
        string: string
        integer: integer
        float: float
        date: date
        boolean: boolean
        list: list
    """
    string = "string"
    integer = "integer"
    float = "float"
    date = "date"
    boolean = "boolean"
    list = "list"


class SysParSchema(BaseModel):
    """System parameters in the Timelink app

    Fields:
        pname: parameter name
        pvalue: parameter value
        ptype: parameter type
        obs: parameter description
    """

    pname: str
    pvalue: str
    ptype: ParTypeSchema
    obs: str

    class Config:
        orm_mode = True

class SysLogSchema(BaseModel):
    """System log in the Timelink app

    Fields:
        seq: sequence number
        time: time of log entry
        level: log level
        origin: origin of log entry
        message: log message
    """

    seq: int
    time: datetime
    level: int
    origin: str
    message: str

    class Config:
        orm_mode = True