import pandas as pd
from sqlalchemy import select

from timelink.api.database import TimelinkDatabase


def entities_with_attribute(
    the_type,
    the_value=None,
    column_name=None,
    entity_type="entity",
    more_info=None,
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
        the_value   : if present, limit to this value, can be SQL wildcard,
        entity_type : if present, limit to this entity type, string
        column_name : if present, use this name for the column, otherwise use the_type
        the_value   : if present, limit to this value, can be SQL wildcard,
        more_info   : List of extra columns from entity_type to add to the dataframe
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

    entity_types = db.get_models_ids()
    if entity_type not in entity_types:
        raise ValueError(f"entity_type must be one of {entity_types}")

    # entity_model = db.get_model(entity_type)
    # get the columns of the entity table, check if more_info is valid
    entity_table = db.get_table(entity_type)
    entity_columns = entity_table.columns.keys()
    if more_info is None:
        more_info = []

    extra_cols = []

    # collect the column objects for the select list
    for mi in more_info:
        if mi not in entity_columns:
            raise ValueError(f"{mi} is not a valid column for {entity_type}")
        else:
            extra_cols.append(entity_table.columns[mi])

    if name_like is not None:
        if "name" not in entity_columns:
            raise (ValueError("To filter by name requires person_info=True."))

    attr = db.get_table("attribute")
    id_col = attr.c.entity.label("id")
    cols = [id_col]
    cols.extend(extra_cols)
    cols.extend(
        [
            attr.c.the_value.label(column_name),
            attr.c.the_date.label(date_column_name),
            attr.c.obs.label(obs_column_name),
        ]
    )

    stmt = (
        select(*cols)
        .where(attr.c.the_type.like(the_type))
        .join(entity_table, entity_table.c.id == attr.c.entity)
    )

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
        stmt = stmt.where(entity_table.columns["name"].like(name_like))

    stmt = stmt.order_by(attr.c.the_date)

    if sql_echo:
        print(f"Query for {the_type}:\n", stmt)

    with db.session() as session:
        records = session.execute(stmt)
        col_names = stmt.columns.keys()
        df = pd.DataFrame.from_records(records, index=["id"], columns=col_names)

    if df.iloc[0].count() == 0:
        return None  # nothing found we

    if more_cols is None:
        more_columns = []
    else:
        more_columns = more_cols

    if len(more_columns) > 0:
        id_col = attr.c.entity

        for mcol in more_columns:
            column_name = mcol
            date_column_name = f"{column_name}.date"
            obs_column_name = f"{column_name}.obs"
            stmt = select(
                attr.c.entity.label("id"),
                attr.c.the_value.label(column_name),
                attr.c.the_date.label(date_column_name),
                attr.c.obs.label(obs_column_name),
            ).where(attr.c.the_type == mcol)
            stmt = stmt.where(id_col.in_(df.index))
            col_names = stmt.columns.keys()

            with db.session() as session:
                records = session.execute(stmt)
                df2 = pd.DataFrame.from_records(
                    records, index=["id"], columns=col_names
                )

            if sql_echo:
                print(f"Query for more_columns={mcol}:\n", stmt)

            if df2.iloc[0].count() == 0:
                df[mcol] = None  # nothing found we set the column to nulls
            else:
                df = df.join(df2)

    return df
