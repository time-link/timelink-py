"""

"""

from sqlalchemy import select
import pandas as pd

from timelink.api.database import TimelinkDatabase
from timelink.api.models import Person


def remove_particles(name, particles=None):
    if particles is None:
        particles = ("de", "da", "e", "das", "dos", "do")

    return " ".join([n for n in name.split() if n not in particles])


def pname_to_df(
    name, db: TimelinkDatabase = None, session=None, similar=False, sql_echo=False
):
    """name_to_df return df of people with a matching name

    Args:
        name = name to search for
        db = database connection to use, either db or session must be specified
        session = session to use, either db or session must be specified
        similar = if true will strip particles and insert a wild card %
                between name components with an extra one at the end
    """
    # We try to use an existing connection and table introspection
    # to avoid extra parameters and going to database too much
    dbsystem: TimelinkDatabase = None
    if db is not None:  # try if we have a db connection in the parameters
        dbsystem = db
    else:  # no session or db connection specified
        raise (
            Exception(
                "must set up a database connection before or specify previously "
                "openned database with db="
            )
        )

    if similar:
        name_particles = remove_particles(name).split(" ")
        name_like = "%".join(name_particles)
        name_like = name_like + "%"
    else:
        name_like = name

    ptable = Person.__table__

    stmt = select(ptable.c.id, ptable.c.name, ptable.c.sex, ptable.c.obs).where(
        ptable.c.name.like(name_like)
    )

    if sql_echo:
        print(stmt)

    if session is not None:
        with session.begin():
            records = session.execute(stmt)
    else:
        with dbsystem.session() as session:
            records = session.execute(stmt)
    df = pd.DataFrame.from_records(
        records.columns("id", "name", "sex", "obs"),
        index=["id"],
        columns=["id", "name", "sex", "obs"],
    )
    if df.iloc[0].count() == 0:
        df = None  # nothing found we
    else:
        df.reset_index(inplace=True)
    return df
