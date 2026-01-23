"""CRUD operations for the Timelink API.

This module provides basic Create, Read, Update, and Delete operations for
Timelink system models, including system parameters, logs, and general entities.
"""

from datetime import datetime
from sqlalchemy.orm import Session  # pylint: disable=import-error
from timelink.api import models
from timelink.api.schemas import EntityAttrRelSchema


def get_syspar(db: Session, q: list[str] | None = None):
    """Retrieve system parameters from the database.

    Args:
        db (Session): Database session.
        q (list[str] | None, optional): List of parameter names to retrieve.
            If None, returns all parameters. Defaults to None.

    Returns:
        list[SysPar]: A list of system parameter objects.
    """
    if q:
        if isinstance(q, str):
            q = [q]
        return db.query(models.SysPar).filter(models.SysPar.pname.in_(q)).all()
    return db.query(models.SysPar).all()


def set_syspar(
    db: Session, syspar: models.SysParSchema
):  # pylint: disable=invalid-name
    """Create or update a system parameter.

    Args:
        db (Session): Database session.
        syspar (SysParSchema): Pydantic schema containing parameter data.

    Returns:
        SysPar: The created or updated system parameter object.
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
    """Retrieve the last n system logs, most recent first.

    Args:
        db (Session): Database session.
        nlogs (int): Number of log entries to retrieve.

    Returns:
        list[SysLog]: A list of system log objects.
    """
    return db.query(models.SysLog).order_by(models.SysLog.seq.desc()).limit(nlogs).all()


def get_syslog_by_time(
    db: Session,  # pylint: disable=invalid-name
    start_time: datetime,
    end_time: datetime,
) -> list[models.SysLog]:
    """Retrieve system logs within a specific time range.

    Args:
        db (Session): Database session.
        start_time (datetime): Start of the time range.
        end_time (datetime): End of the time range.

    Returns:
        list[SysLog]: A list of system log objects within the specified range.
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
    """Create a new system log entry.

    Args:
        db (Session): Database session.
        log (SysLogCreateSchema): Pydantic schema containing level, origin, and message.

    Returns:
        SysLog: The created system log object.
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
    pentity = EntityAttrRelSchema.model_validate(entity)
    # get the relations of this entity

    # TODO return the entity as a dictionary with rels in and out
    #       and contains

    return pentity
