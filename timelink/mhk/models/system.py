""" Models for system tables

Tables defined here:

    - syspar: system parameters
    - syslog: system log

"""

from enum import Enum
from typing import Optional

from datetime import datetime
from pydantic import BaseModel, ConfigDict  # pylint: disable=import-error

from sqlalchemy import Column, String, Integer, DateTime  # pylint: disable=import-error
from sqlalchemy.sql import func  # pylint: disable=import-error
from sqlalchemy.orm import mapped_column  # pylint: disable=import-error
from sqlalchemy.orm import Mapped  # pylint: disable=import-error
from timelink.mhk.models.base_class import Base


class SysPar(Base):
    """System parameters table"""

    __tablename__ = "syspar"
    pname = Column(String, primary_key=True, index=True)
    pvalue = Column(String)
    ptype = Column(String)
    obs = Column(String)


class ParTypeSchema(str, Enum):
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

    model_config = ConfigDict(from_attributes=True)


class LogLevel(str, Enum):
    """Log level

    Fields:
        debug: debug
        info: info
        warning: warning
        error: error
        critical: critical
    """

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class SysLog(Base):
    """System log table

    Fields:
        seq: sequence number
        time: time of log entry
        level: log level
        origin: origin of log entry
        message: log message
    """

    seq = Column(Integer, primary_key=True, index=True, autoincrement=True)
    time = Column(DateTime, default=func.now())
    level = Column(Integer)
    origin = Column(String)
    message = Column(String)


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
    level: LogLevel
    origin: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class SysLogCreateSchema(BaseModel):
    """System log create in the Timelink app

    Fields:
        level: log level
        origin: origin of log entry
        message: log message
    """

    level: LogLevel
    origin: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class KleioImportedFile(Base):
    """Represents a Kleio file imported in the database

    Fields:
        path: path of the file
        name: name of the file
        structure: structure name
        translator: translator name
        translation_date: date of translation
        nerrors: number of errors
        nwarnings: number of warnings
        error_rpt: error report
        warning_rpt: warning report"""

    __tablename__ = "kleiofiles"

    path: Mapped[str] = mapped_column(String(1024), primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    structure: Mapped[str] = mapped_column(String(255), nullable=False)
    translator: Mapped[str] = mapped_column(String(255), nullable=False)
    translation_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    nerrors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    nwarnings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_rpt: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    warning_rpt: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    imported: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    imported_string: Mapped[str] = mapped_column(String(255), nullable=False)
