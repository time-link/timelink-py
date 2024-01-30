""" Utilities to support
Notebook integration of
Timelink data

Utilities and shared variables for using timelink inside notebooks

:Contains:
    Utilities for acessing timelink from Jupyter notebooks

(c) Joaquim Carvalho, MIT LICENSE

"""

import logging
import datetime
import socket

from sqlalchemy import MetaData, Table, engine, inspect, text

# import to expose to notebooks
from .timelink_notebook import TimelinkNotebook   # noqa
from timelink.api.database import get_postgres_dbnames  # noqa
from timelink.api.database import get_sqlite_databases  # noqa
from timelink.api.database import TimelinkDatabase  # noqa
from timelink.api.database import is_valid_postgres_db_name  # noqa

from timelink.kleio import KleioServer  # noqa

from timelink.mhk.utilities import get_connection_string
from timelink.mhk.models import base  # noqa
from timelink.mhk.models.person import Person
from timelink.mhk.models.db import TimelinkMHK


import timelink.notebooks.config as conf

current_time = datetime.datetime.now()
current_machine = socket.gethostname()

mhk_databases = []


def get_db(db_spec, **extra_args):
    """get a TimelinkMHK Database

    db_spec can be a connection string or a tuple.
    if a tuple:
        ('mhk','mhk_db_name') or
        ('sqlite','db_file')
    """
    if type(db_spec) is str:
        db = "string"
        name = db_spec
    else:
        try:
            db, name = db_spec
        except Exception:
            logging.exception(
                "Database specification must either be a string of a tuple (db,name)"
            )

    if db == "mhk":
        tlink_db = get_mhk_db(name, **extra_args)
    elif db == "sqlite":
        tlink_db = get_sqlite_db(name, **extra_args)
    elif db == "string":
        con_string = name
        conf.TIMELINK_CONNSTRING = con_string  # share it with other modules
        tlink_db = TimelinkMHK(con_string, **extra_args)
        conf.TIMELINK_DBSYSTEM = db  # share it
        conf.Session.configure(bind=db.get_engine())
    else:
        logging.error(f"Unrecognized database specification. Type: {db} name: {name}")
        return None

    return tlink_db


def get_sqlite_db(db_name, **extra_args):
    """Create a connection to a Timelink/Sqlite database

    Assumes the database is in the directory ../database/sqlite3/

    """
    connection_string = (
        f"sqlite:///../database/sqlite3/{db_name}?check_same_thread=False"
    )
    conf.TIMELINK_CONNSTRING = connection_string  # share it with other modules
    db = TimelinkMHK(connection_string, **extra_args)
    conf.TIMELINK_DBSYSTEM = db  # share it
    conf.Session.configure(bind=db.get_engine())
    return db


def get_mhk_db(db_name, **extra_args) -> TimelinkMHK:
    """Create a connection to a Timelink/MHK database

    Creates a connection to the database db_name,
    using the parameters of the current MHK instalation.

    The resulting dbsystem oject is stored in global variable
    TIMELINK_DBSYSTEM

    """

    connection_string = get_connection_string(db_name)
    conf.TIMELINK_CONNSTRING = connection_string  # share it with other modules
    db = TimelinkMHK(connection_string, **extra_args)
    conf.TIMELINK_DBSYSTEM = db  # share it
    conf.Session.configure(bind=db.get_engine())
    return db


def get_nattribute_table(db: TimelinkMHK = None):
    """Return the nattribute view.

    Returns a sqlalchemy table linked to the nattributes view of MHK databases
    This views joins the table "persons" and the table "attributes" providing attribute
    values with person names and sex.

    The column id contains the id of the person/object, not of the attribute
    """

    # TODO View creation should go to timelink-py
    nattribute_sql = """
        CREATE VIEW nattributes AS
                    SELECT p.id        AS id,
                        p.name      AS name,
                        p.sex       AS sex,
                        a.the_type  AS the_type,
                        a.the_value AS the_value,
                        a.the_date  AS the_date,
                        p.obs       AS pobs,
                        a.obs       AS aobs
                    FROM attributes a
                        JOIN persons p
                    WHERE (a.entity = p.id)
        """
    if db is not None:
        dbsystem = db
    elif conf.TIMELINK_DBSYSTEM is not None:
        dbsystem = conf.TIMELINK_DBSYSTEM
    else:
        raise (Exception("must specify database with db="))
    if conf.TIMELINK_NATTRIBUTES is None:
        eng: engine = dbsystem.get_engine()
        metadata: MetaData = dbsystem.get_metadata()
        insp = inspect(eng)
        if (
            "nattributes" in insp.get_view_names()
            or "nattributes" in insp.get_table_names()  # noqa
        ):
            pass
        else:
            with eng.connect() as con:
                con.execute(text(nattribute_sql))

        attr = Table("nattributes", metadata, autoload_with=eng)
        conf.TIMELINK_NATTRIBUTES = attr
    else:
        attr = conf.TIMELINK_NATTRIBUTES
    return attr


def get_attribute_table(db: TimelinkMHK = None):
    """Return the attribute table.

    Returns a sqlalchemy table linked to the attributes table of MHK databases

            id        varchar(64)    not null  primary key,
            entity    varchar(64)    null,
            the_type  varchar(512)   null,
            the_value varchar(1024)  null,
            the_date  varchar(24)    null,
            obs       varchar(16000) null

    The column id contains the id of the attribute and the column entity the id
    of the person/object to which the attribute is related
    """
    if db is not None:
        dbsystem = db
    elif conf.TIMELINK_DBSYSTEM is not None:
        dbsystem = conf.TIMELINK_DBSYSTEM
    else:
        raise (Exception("must specify database with db="))
    if conf.TIMELINK_ATTRIBUTES is None:
        eng: engine = dbsystem.get_engine()
        metadata: MetaData = dbsystem.get_metadata()
        attr = Table("attributes", metadata, autoload_with=eng)
        conf.TIMELINK_ATTRIBUTES = attr
    else:
        attr = conf.TIMELINK_ATTRIBUTES
    return attr


def get_person_table(db: TimelinkMHK = None):
    """Return the person table.

    Returns a sqlalchemy table linked to the persons table of MHK databases


    """
    if db is not None:
        dbsystem = db
    elif conf.TIMELINK_DBSYSTEM is not None:
        dbsystem = conf.TIMELINK_DBSYSTEM
    else:
        raise (Exception("must specify database with db="))
    if conf.TIMELINK_PERSONS is None:
        eng: engine = dbsystem.get_engine()
        metadata: MetaData = dbsystem.get_metadata()
        pers = Table("persons", metadata, autoload_with=eng)
        conf.TIMELINK_PERSONS = pers
    else:
        pers = conf.TIMELINK_PERSONS
    return pers


def get_relations_table(db: TimelinkMHK = None):
    """Return the relations table.

    Returns a sqlalchemy table linked to the relations table of MHK databases


            id          varchar(64)    not null primary key,
            origin      varchar(64)    null,
            destination varchar(64)    null,
            the_date    varchar(24)    null,
            the_type    varchar(32)    null,
            the_value   varchar(256)   null,
            obs         varchar(16000) null

    """
    if db is not None:
        dbsystem = db
    elif conf.TIMELINK_DBSYSTEM is not None:
        dbsystem = conf.TIMELINK_DBSYSTEM
    else:
        raise (Exception("must specify database with db="))
    if conf.TIMELINK_RELATIONS is None:
        eng: engine = dbsystem.get_engine()
        metadata: MetaData = dbsystem.get_metadata()
        rels = Table("relations", metadata, autoload_with=eng)
        conf.TIMELINK_RELATIONS = rels
    else:
        rels = conf.TIMELINK_RELATIONS
    return rels


def get_nfuncs_view(db: TimelinkMHK = None):
    """Return the nfuncs (named functions) table.

    Returns a sqlalchemy table linked to the nfuncs view of MHK databases



    """

    nfuncs_sql = """
        CREATE VIEW nfuncs AS
            SELECT
                r.origin    AS id,
                p.name,
                r.the_value AS func,
                a.id        AS id_act,
                a.the_type  AS act_type,
                a.the_date  AS act_date
            FROM relations r, persons p, acts a
            WHERE r.the_type = 'function-in-act' AND r.destination = a.id AND r.origin = p.id;
    """
    if db is not None:
        dbsystem = db
    elif conf.TIMELINK_DBSYSTEM is not None:
        dbsystem = conf.TIMELINK_DBSYSTEM
    else:
        raise (Exception("must specify database with db="))
    if conf.TIMELINK_NFUNCS is None:
        eng: engine = dbsystem.get_engine()
        metadata: MetaData = dbsystem.get_metadata()
        insp = inspect(eng)
        if "nfuncs" in insp.get_view_names() or "nfuncs" in insp.get_table_names():
            pass
        else:
            with eng.connect() as con:
                con.execute(text(nfuncs_sql))

        nfuncs = Table("nfuncs", metadata, autoload_with=eng)
        conf.TIMELINK_NFUNCS = nfuncs
    else:
        nfuncs = conf.TIMELINK_NFUNCS
    return nfuncs


def get_person(id: str = None, db=None, sql_echo: bool = False) -> Person:
    """
    Fetch a person from the database
    """
    if id is None:
        raise (Exception("Error, id needed"))
    p: Person = db.session().get(Person, id)
    return p


def pperson(id: str):
    """Prints a person in kleio notation"""
    print(get_person(id=id).to_kleio())
