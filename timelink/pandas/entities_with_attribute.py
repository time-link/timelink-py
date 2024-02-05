import pandas as pd
from sqlalchemy import select

from timelink.api.database import TimelinkDatabase


def entities_with_attribute(
    the_type,
    the_value=None,
    column_name=None,
    person_info=True,
    dates_in=None,
    name_like=None,
    filter_by=None,
    more_cols=None,
    db: TimelinkDatabase = None,
    sql_echo=False,
):
    """Generate a pandas dataframe with entities with a given attribute

    Args:
        the_type    : type of attribute, can have SQL wildcards, string
        column_name : if present, use this name for the column, otherwise use the_type
        the_value   : if present, limit to this value, can be SQL wildcard,
                       string or list of strings
        person_info : if True add name and sex of person, otherwise just id
        dates_in    : (after,before) if present only between those dates (exclusive)
        name_like   : name must match pattern (will set person_info = True),
        filter_by   : list of ids, limit to these
        more_cols   : add more attributes if available
        db          : A TimelinkMHK object
        sql_echo    : if True echo the sql generated

    Note that if person_info = True the columns 'name' and 'sex' will be added.

    Ideas:
        Add :
            the_value_in: (list of values)
            the_value_between_inc (min, max, get >=min and <= max)
            the_value_between_exc (min, max, get >min and < max)
        accept a list of the_type and return a dataframe with all of them

    """
    # We try to use an existing connection and table introspection
    # to avoid extra parameters and going to database too much
    dbsystem: TimelinkDatabase = db
    if dbsystem is None:
        raise (
            Exception(
                "db: TimelinkDatabase required. Must create  to set up a database connection"
            )
        )

        # if we dont have a name for the column we use the attribute type sanitized
    if column_name is None:
        column_name = the_type
    date_column_name = f"{column_name}.date"
    obs_column_name = f"{column_name}.obs"

    if name_like is not None:
        if person_info is not None and not person_info:
            raise (ValueError("To filter by name requires person_info=True."))
        person_info = True

    if person_info:  # to fetch person info we need nattributes view
        attr = db.get_nattribute_view()
        id_col = attr.c.id
        stmt = select(
            attr.c.id,
            attr.c.name.label("name"),
            attr.c.sex.label("sex"),
            attr.c.the_value.label(column_name),
            attr.c.the_date.label(date_column_name),
            attr.c.aobs.label(obs_column_name),
        ).where(attr.c.the_type.like(the_type))
        cols = ["id", "name", "sex", column_name, date_column_name, obs_column_name]
    else:  # no person information required we use the attributes table
        attr = db.get_nattribute_table()
        id_col = attr.c.entity
        stmt = select(
            attr.c.entity,
            attr.c.the_value.label(column_name),
            attr.c.the_date.label(date_column_name),
            attr.c.obs.label(obs_column_name),
        ).where(attr.c.the_type.like(the_type))
        cols = ["id", column_name, date_column_name, obs_column_name]

    # Filter by value
    if the_value is not None:
        if type(the_value) is list:
            stmt = stmt.where(attr.c.the_value.in_(the_value))
        elif type(the_value) is str:
            stmt = stmt.where(attr.c.the_value.like(the_value))
        else:
            raise ValueError("the_value must be either a string or a list of strings")

    # filter by id list
    if filter_by is not None:
        stmt = stmt.where(id_col.in_(filter_by))

    # filter by date
    if dates_in is not None:
        after_date, before_date = dates_in

        stmt = stmt.where(attr.c.the_date > after_date, attr.c.the_date < before_date)

    # filter by name
    if name_like is not None:
        stmt = stmt.where(attr.c.name.like(name_like))

    stmt = stmt.order_by(attr.c.the_date)

    if sql_echo:
        print(f"Query for {the_type}:\n", stmt)

    with db.session() as session:
        records = session.execute(stmt)
        df = pd.DataFrame.from_records(records, index=["id"], columns=cols)

    if df.iloc[0].count() == 0:
        return None  # nothing found we

    if more_cols is None:
        more_columns = []
    else:
        more_columns = more_cols

    if len(more_columns) > 0:
        attr = db.get_nattribute_view()
        id_col = attr.c.id

        for mcol in more_columns:
            column_name = mcol
            date_column_name = f"{column_name}.date"
            obs_column_name = f"{column_name}.obs"
            stmt = select(
                attr.c.id,
                attr.c.the_value.label(column_name),
                attr.c.the_date.label(date_column_name),
                attr.c.aobs.label(obs_column_name),
            ).where(attr.c.the_type == mcol)
            stmt = stmt.where(id_col.in_(df.index))
            cols = ["id", column_name, date_column_name, obs_column_name]

            with db.session() as session:
                records = session.execute(stmt)
                df2 = pd.DataFrame.from_records(records, index=["id"], columns=cols)

            if sql_echo:
                print(f"Query for more_columns={mcol}:\n", stmt)

            if df2.iloc[0].count() == 0:
                df[mcol] = None  # nothing found we set the column to nulls
            else:
                df = df.join(df2)

    return df
