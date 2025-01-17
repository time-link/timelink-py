""" """

from typing import List
import pandas as pd
from sqlalchemy.sql import select
from timelink.api.database import TimelinkDatabase


def entities_with_attribute(
    the_type: str | List[str],
    the_value=None,
    column_name=None,
    entity_type="entity",
    show_elements=None,
    dates_in=None,
    name_like=None,
    filter_by=None,
    more_attributes=None,
    db: TimelinkDatabase = None,
    sql_echo=False,
):
    """Generate a pandas dataframe with entities with a given attribute

    Args:
        the_type    : type of attribute, can have SQL wildcards, string, or list
        the_value   : if present, limit to this value, can be SQL wildcard,
        entity_type : if present, limit to this entity type, string
        column_name : if present, use this name for the attribute column, otherwise use the_type
                      usefull when the_type is a list
        name_like   : if present, limit to this name, can have SQL wildcards
        show_elements: List of entity elements to add to the dataframe
        dates_in    : (after,before) if present only between those dates (exclusive)
        filter_by   : list of ids, limit to these entities
        more_attributes: add more attributes if available
        db          : A TimelinkMHK object
        sql_echo    : if True echo the sql generated

    Example:
        # name, sex and function of people living in the same place

        neighbors = entities_with_attribute(
                                entity_type="person",
                                show_elements=["groupname","names","sex"],
                                the_type='residencia',
                                the_value="soure"
                                column_name="local", # use this istead of "residencia"
                                more_attributes=["profissao"]
                                )

    Notes:
        - The function will return a dataframe with the columns:
            id, group

    Ideas:
        Add :
            the_value_in: (list of values)
            the_value_between_inc (min, max, get >=min and <= max)
            the_value_between_exc (min, max, get >min and < max)


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
        # if the_type is a list or a string
        if type(the_type) is list:
            column_name = "_".join(the_type)
        else:
            column_name = str(the_type)
    date_column_name = f"{column_name}.date"
    obs_column_name = f"{column_name}.obs"
    type_column_name = f"{column_name}.type"
    line_column_name = f"{column_name}.line"
    level_column_name = f"{column_name}.level"
    attribute_extra_info_column_name = f"{column_name}.extra_info"

    entity_types = db.get_models_ids()
    if entity_type not in entity_types:
        raise ValueError(f"entity_type must be one of {entity_types}")

    entity_model = db.get_model(entity_type)
    # get the columns of the entity table, check if more_info is valid
    entity_columns = select(entity_model).selected_columns.keys()
    entity_id_col = select(entity_model).selected_columns["id"]

    if show_elements is None:
        show_elements = []

    extra_cols = []

    # collect the column objects for the select list
    for mi in show_elements:
        if mi not in entity_columns:
            raise ValueError(f"{mi} is not a valid column for {entity_type}")
        else:
            extra_cols.append(select(entity_model).selected_columns[mi])

    if name_like is not None:
        if "name" not in entity_columns:
            raise (ValueError("To filter by name requires name in the show_elements list."))

    attr = db.create_eattribute_view()
    # id_col = attr.c.entity.label("id")
    cols = [entity_id_col]
    cols.extend(extra_cols)
    more_info_cols = cols.copy()
    cols.extend(
        [
            attr.c.the_type.label(type_column_name),
            attr.c.the_value.label(column_name),
            attr.c.the_date.label(date_column_name),
            attr.c.the_line.label(line_column_name),
            attr.c.the_level.label(level_column_name),
            attr.c.aobs.label(obs_column_name),
            attr.c.a_extra_info.label(attribute_extra_info_column_name),
        ]
    )

    if type(the_type) is list:
        attribute_query = attr.c.the_type.in_(the_type)
    else:
        attribute_query = attr.c.the_type.like(the_type)

    # filter by id list
    if filter_by is not None:
        # in some cases the filter_by list
        #  may contain ids that are not in the attribute table
        #  we need to add them to the final dataframe
        filter_by_sql = (
            select(entity_model)
            .with_only_columns(*more_info_cols, maintain_column_froms=True)
            .where(entity_model.id.in_(filter_by))
        )
        with db.session() as session:
            filtered_by_rows = session.execute(filter_by_sql)
            col_names = filter_by_sql.selected_columns.keys()
            filtered_df = pd.DataFrame.from_records(
                filtered_by_rows, index=["id"], columns=col_names
            )

        stmt = (
            (select(entity_model).where(entity_id_col.in_(filter_by)))
            .join(attr, attr.c.entity == entity_model.id, isouter=True)
            .where(attribute_query)
            .with_only_columns(*cols)
        )
    else:
        stmt = (
            select(entity_model)
            .join(attr, attr.c.entity == entity_model.id)
            .where(attribute_query)
            .with_only_columns(*cols)
        )

    # Filter by value
    if the_value is not None:
        if type(the_value) is list:
            stmt = stmt.where(attr.c.the_value.in_(the_value))
        elif type(the_value) is str:
            stmt = stmt.where(attr.c.the_value.like(the_value))
        else:
            raise ValueError("the_value must be either a string or a list of strings")

    # filter by date
    if dates_in is not None:
        after_date, before_date = dates_in

        stmt = stmt.where(attr.c.the_date > after_date, attr.c.the_date < before_date)

    # filter by name
    if name_like is not None:
        stmt = stmt.where(select(entity_model).selected_columns["name"].like(name_like))

    stmt = stmt.order_by(attr.c.the_date)

    if sql_echo:
        print(f"Query for {the_type}:\n", stmt)

    with db.session() as session:
        records = session.execute(stmt)
        col_names = stmt.selected_columns.keys()
        df = pd.DataFrame.from_records(records, index=["id"], columns=col_names)
        if df.iloc[0].count() == 0:
            return None  # nothing found we return None
        # Check for extra info
        extra_info_edits = []
        for row_number, (_, row) in enumerate(df.iterrows()):
            # Perform operations using row_number, index, and row
            if row[attribute_extra_info_column_name] is not None:
                extra_info: dict = row[attribute_extra_info_column_name]
                for key, value in extra_info.items():
                    if key != "value":
                        xtra_col_name = f"{column_name}.{key}"
                    else:
                        xtra_col_name = column_name
                    for aspect, avalue in value.items():
                        xtra_col_name = f"{xtra_col_name}.{aspect}"
                        extra_info_edits.append((row_number, xtra_col_name, avalue))
        for row_number, xtra_col_name, avalue in extra_info_edits:
            if xtra_col_name not in df.columns:
                df[xtra_col_name] = None
            df.iat[row_number, df.columns.get_loc(xtra_col_name)] = avalue

    if filter_by is not None:
        fb_ids = filtered_df.index.unique()
        attr_ids = df.index.unique()
        missing = list(set(fb_ids) - set(attr_ids))
        if len(missing) > 0:
            missing_df = filtered_df.loc[missing]
            df = pd.concat([df, missing_df])

    if df.iloc[0].count() == 0:
        return None  # nothing found we

    if more_attributes is None:
        more_columns = []
    else:
        more_columns = more_attributes

    if len(more_columns) > 0:
        for mcol in more_columns:
            column_name = mcol
            date_column_name = f"{column_name}.date"
            obs_column_name = f"{column_name}.obs"
            extra_info_column_name = f"{column_name}.extra_info"
            stmt = select(
                attr.c.entity.label("id"),
                attr.c.the_value.label(column_name),
                attr.c.the_date.label(date_column_name),
                attr.c.aobs.label(obs_column_name),
                attr.c.a_extra_info.label(extra_info_column_name),
            ).where(attr.c.the_type == mcol
                    ).where(attr.c.entity.in_(df.index))
            # col_names = stmt.columns.keys()

            with db.session() as session:
                records = session.execute(stmt)
                col_names = stmt.selected_columns.keys()

                df2 = pd.DataFrame.from_records(
                    records, index=["id"], columns=col_names
                )
                if df2.iloc[0].count() > 0:
                    extra_info_edits = []
                    for row_number, (_, row) in enumerate(df2.iterrows()):
                        if row[extra_info_column_name] is not None:
                            extra_info: dict = row[extra_info_column_name]
                            for key, value in extra_info.items():
                                if key != "value":
                                    xtra_col_name = f"{column_name}.{key}"
                                else:
                                    xtra_col_name = column_name
                                for aspect, avalue in value.items():
                                    xtra_col_name2 = f"{xtra_col_name}.{aspect}"
                                    extra_info_edits.append(
                                        (row_number, xtra_col_name2, avalue)
                                    )
                    for row_number, xtra_col_name2, avalue in extra_info_edits:
                        if xtra_col_name2 not in df2.columns:
                            df2[xtra_col_name2] = None
                        df2.iat[row_number, df2.columns.get_loc(xtra_col_name2)] = avalue

            if sql_echo:
                print(f"Query for more_attributes={mcol}:\n", stmt)

            if df2.iloc[0].count() == 0:
                df[mcol] = None  # nothing found we set the column to nulls
            else:
                df = df.join(df2)

            # use extra_info to add more columns

    return df
