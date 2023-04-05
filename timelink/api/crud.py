""" CRUD operations for the timelink API. """
from datetime import datetime
from sqlalchemy.orm import Session # pylint: disable=import-error
from timelink.api import models, schemas

def get_syspar(db: Session, pname: str):
    """Get system parameter
    Args:
        db: database session
        pname: parameter name
    Returns:
        SysPar object
    """
    return db.query(models.SysPar).filter(models.SysPar.pname == pname).first()

def get_syspar(db: Session, q: list[str] | None = None):
    """Get system parameters
    Args:
        db: database session
        q: parameter name(s); if empty, return all parameters
    Returns:
        SysPar object
    """
    if q:
        if isinstance(q, str):
            q = [q]
        return db.query(models.SysPar).filter(models.SysPar.pname.in_(q)).all()
    return db.query(models.SysPar).all()

def set_syspar(db: Session, syspar: models.SysParSchema):
    """Set system parameters
    Args:
        db: database session
        syspar: SysPar object
    Returns:
        SysPar object
    """
    db_syspar = get_syspar(db, syspar.pname)
    if db_syspar:
        db_syspar.pvalue = syspar.pvalue
        db_syspar.ptype = syspar.ptype
        db_syspar.obs = syspar.obs
    else:
        db_syspar = models.SysPar(pname=syspar.pname,
                                  pvalue=syspar.pvalue,
                                  ptype=syspar.ptype,
                                  obs=syspar.obs)
        db.add(db_syspar)
    db.commit()
    db.refresh(db_syspar)
    return db_syspar    

def get_syslog(db: Session, nlogs: int) -> list[models.SysLog]:
    """Get last n system logs last one first
    Args:
        db: database session
        nlogs: sequence number
    Returns:
        List of SysLog objects
    """
    return db.query(models.SysLog).order_by(models.SysLog.seq.desc()).limit(nlogs)


def get_syslog_by_time(db: Session, start_time: datetime, end_time: datetime) -> list[models.SysLog]:
    """Get system logs between start_time and end_time
    Args:
        db: database session
        start_time: start time
        end_time: end time
    Returns:
        List of SysLog objects
    """
    return db.query(models.SysLog).filter(models.SysLog.time >= start_time).filter(models.system.SysLog.time <= end_time).all()

def set_syslog(db: Session, origin: str, message: str, level: int) -> models.system.SysLog:
    """Set system log
    Args:
        db: database session
        origin: origin of the log message
        message: log message
        level: log level
    Returns:
        SysLog object
    """
    db_syslog = models.SysLog(origin=origin, message=message, level=level)
    db.add(db_syslog)
    db.commit()
    db.refresh(db_syslog)
    return db_syslog
   