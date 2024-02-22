""" CRUD operations for the timelink API. """

from datetime import datetime
from sqlalchemy.orm import Session  # pylint: disable=import-error
from timelink.api import models
from timelink.api.schemas import EntityAttrRelSchema


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


def set_syspar(
    db: Session, syspar: models.SysParSchema
):  # pylint: disable=invalid-name
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
        db_syspar = models.SysPar(
            pname=syspar.pname, pvalue=syspar.pvalue, ptype=syspar.ptype, obs=syspar.obs
        )
        db.add(db_syspar)
    db.commit()
    db.refresh(db_syspar)
    return db_syspar


def get_syslog(
    db: Session, nlogs: int
) -> list[models.SysLog]:  # pylint: disable=invalid-name
    """Get last n system logs last one first
    Args:
        db: database session
        nlogs: sequence number
    Returns:
        List of SysLog objects
    """
    return db.query(models.SysLog).order_by(models.SysLog.seq.desc()).limit(nlogs).all()


def get_syslog_by_time(
    db: Session,  # pylint: disable=invalid-name
    start_time: datetime,
    end_time: datetime,
) -> list[models.SysLog]:
    """Get system logs between start_time and end_time
    Args:
        db: database session
        start_time: start time
        end_time: end time
    Returns:
        List of SysLog objects
    """
    return (
        db.query(models.SysLog)
        .filter(models.SysLog.time >= start_time)
        .filter(models.system.SysLog.time <= end_time)
        .all()
    )


def set_syslog(
    db: Session, log: models.system.SysLogCreateSchema
) -> models.system.SysLog:  # pylint: disable=invalid-name
    """Set system log
    Args:
        db: database session
        log: SysLogCreateSchema object with level, origin and message
    Returns:
        SysLog object
    """
    db_syslog = models.SysLog(origin=log.origin, message=log.message, level=log.level)
    db.add(db_syslog)
    db.commit()
    db.refresh(db_syslog)
    return db_syslog


def get(db: Session, id: str) -> EntityAttrRelSchema:  # pylint: disable=invalid-name
    """Get entity by id
    Args:
        db: database session
        id: entity id
    Returns:
        Entity object
    """
    entity = models.Entity.get_entity(id, db)
    # get the columns of this entity
    pentity = EntityAttrRelSchema.from_orm(entity)
    # get the relations of this entity

    # TODO return the entity as a dictionary with rels in and out
    #       and contains

    return pentity
