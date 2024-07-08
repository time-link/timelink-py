"""
Create a dataframe with the values of an attribute
"""

import pandas as pd

from sqlalchemy import select, func, and_, desc

from timelink.api.database import TimelinkDatabase


def attribute_values(
    attr_type,
    groupname=None,
    dates_between=None,
    db: TimelinkDatabase = None,
    sql_echo=False,
):
    """Return the vocabulary of an attribute

    The returned dataframe has a row for each unique value
    a 'count' with the number of different entities, and
    the the first and last date for that row

    Args:
        attr_type = attribute type to search for
        groupname = groupname to filter by (str or list), if None all groups counted
        db = database connection to use, either db or session must be specified
        dates_between = tuple with two dates in format yyyy-mm-dd
        sql_echo = if true will print the sql statement


    To filter by dates: dates_in = (from_date,to_date)
    with dates in format yyyy-mm-dd
    will return attributes with
    from_date < date < to_date

    """

    #  We try to use an existing connection and table introspection
    # to avoid extra parameters and going to database too much
    dbsystem: TimelinkDatabase = None
    if db is not None:  # try if we have a db connection in the parameters
        dbsystem = db
    else:
        raise Exception(
            "No database connection specified, must set up a database"
            " connection before or specify previously openned database"
            " with db="
        )

    attr_table = db.get_eattribute_view()
    entities_table = db.get_table("entity")

    if dates_between is not None:
        first_date, last_date = dates_between
        stmt = select(
            attr_table.c.the_value.label("value"),
            func.count(attr_table.c.entity.distinct()).label("count"),
            func.min(attr_table.c.the_date).label("date_min"),
            func.max(attr_table.c.the_date).label("date_max"),
        ).where(
            and_(
                attr_table.c.the_type == attr_type,
                attr_table.c.the_date > first_date.strip("-"),
                attr_table.c.the_date < last_date.strip("-"),
            )
        )

    else:
        stmt = select(
            attr_table.c.the_value.label("value"),
            func.count(attr_table.c.entity.distinct()).label("count"),
            func.min(attr_table.c.the_date).label("date_min"),
            func.max(attr_table.c.the_date).label("date_max"),
        ).where(attr_table.c.the_type == attr_type)

    if groupname is not None:
        if isinstance(groupname, list):
            stmt = stmt.where(
                select(entities_table.c.id)
                .where(
                    and_(
                        entities_table.c.id == attr_table.c.entity,
                        entities_table.c.groupname.in_(groupname),
                    )
                )
                .exists()
            )

        else:
            # where entity exists in entities with groupname = groupname
            stmt = stmt.where(
                select(entities_table.c.id)
                .where(
                    and_(
                        entities_table.c.id == attr_table.c.entity,
                        entities_table.c.groupname == groupname,
                    )
                )
                .exists()
            )

    stmt = stmt.group_by(attr_table.c.the_value).order_by(desc("count"))

    if sql_echo:
        print(stmt)

    with dbsystem.session() as session:
        records = session.execute(stmt)
    df = pd.DataFrame.from_records(
        records, index=["value"], columns=["value", "count", "date_min", "date_max"]
    )

    return df
