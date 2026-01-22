# pyright: reportArgumentType=false
# pyright: reportCallIssue=false
# pyright: reportAssignmentType=false
# pyright: reportAttributeAccessIssue=false

from typing import List

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from timelink.api.database import TimelinkDatabase
from timelink.api.models.entity import Entity


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
    db: TimelinkDatabase | None = None,
    session: Session | None = None,
    sql_echo=False,
):
    """Generate a pandas DataFrame of entities filtered by attributes.

    Args:
        the_type: Attribute type (string, SQL wildcard, or list of types).
        the_value: Optional value filter (string, SQL wildcard, or list of strings).
        column_name: Optional column name to use for the attribute values.
        entity_type: Entity model to query (default "entity").
        show_elements: Entity columns to include in the result.
        dates_in: Tuple ``(after, before)`` to constrain attribute dates (exclusive).
        name_like: Optional SQL LIKE filter on the entity name.
        filter_by: List of entity ids to include even if attributes are missing.
        more_attributes: Additional attribute types to join into the result.
        db: TimelinkDatabase instance (required if session is not provided).
        session: SQLAlchemy session; if omitted, one is created from ``db``.
        sql_echo: When True, echo the generated SQL statements.

    Returns:
        pandas.DataFrame or None when no rows match. Result columns include the requested
        entity fields plus attribute value, date, observation, type, line, level,
        attr_id, groupname, and any available extra_info entries.
    """
    # We try to use an existing connection and table introspection
    # to avoid extra parameters and going to database too much
    if db is None:
        raise (
            Exception(
                "db: TimelinkDatabase required. Must create  to set up a database connection"
            )
        )

    mysession: Session
    if session is None:
        mysession = db.session()
    else:
        mysession = session

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
    atr_id_column_name = f"{column_name}.attr_id"
    atr_group_column_name = f"{column_name}.groupname"
    attribute_extra_info_column_name = f"{column_name}.extra_info"

    entity_types = db.get_models_ids()
    if entity_type not in entity_types:
        raise ValueError(f"entity_type must be one of {entity_types}")

    entity_model: Entity = db.get_model(entity_type)  # type: ignore
    # get the columns of the entity table, check if more_info is valid
    entity_columns = select(entity_model).selected_columns.keys()  # type: ignore[reportCallIssue]
    entity_id_col = select(entity_model).selected_columns["id"]  # type: ignore

    if show_elements is None:
        show_elements = []

    extra_cols = []

    # collect the column objects for the select list
    for mi in show_elements:
        if mi not in entity_columns:
            raise ValueError(f"{mi} is not a valid column for {entity_type}")
        else:
            extra_cols.append(select(entity_model).selected_columns[mi])  # type: ignore[assignment]

    if name_like is not None:
        if "name" not in entity_columns:
            raise (
                ValueError("To filter by name requires name in the show_elements list.")
            )

    attr = db.get_view("eattributes")
    # id_col = attr.c.entity.label("id")
    cols = [entity_id_col]
    cols.extend(extra_cols)
    more_info_cols = cols.copy()
    cols.extend(
        [
            attr.c.attr_id.label(atr_id_column_name),
            attr.c.the_type.label(type_column_name),
            attr.c.the_value.label(column_name),
            attr.c.the_date.label(date_column_name),
            attr.c.a_the_line.label(line_column_name),
            attr.c.a_the_level.label(level_column_name),
            attr.c.a_groupname.label(atr_group_column_name),
            attr.c.aobs.label(obs_column_name),
            attr.c.a_extra_info.label(attribute_extra_info_column_name),
        ]
    )

    if type(the_type) is list:
        attribute_query = attr.c.the_type.in_(the_type)
    else:
        attribute_query = attr.c.the_type.like(the_type)

    # filter by id list
    filtered_df: pd.DataFrame = pd.DataFrame()
    if filter_by is not None:

        # in some cases the filter_by list
        #  may contain ids that are not in the attribute table
        #  we need to add them to the final dataframe
        filter_by_sql = (
            select(entity_model)  # type: ignore
            .with_only_columns(*more_info_cols, maintain_column_froms=True)
            .where(entity_model.id.in_(filter_by))  # type: ignore
        )
        with mysession as session:
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

    with mysession as session:
        records = session.execute(stmt)
        col_names = stmt.selected_columns.keys()
        df = pd.DataFrame.from_records(records, index=["id"], columns=col_names)
        if df.empty or df.iloc[0].count() == 0:
            return None  # nothing found we return None
        # Check for extra info.
        extra_info_edits = []
        for row_number, (_, row) in enumerate(df.iterrows()):
            # Perform operations using row_number, index, and row
            if row[attribute_extra_info_column_name] is not None:
                # get the extra_info dict from the row
                # the dict contains information stored during the import
                # process that is not stored directly in the attribute/columns
                # of the database. These include: comment and original aspects,
                # the element name and class in the original source
                # and the attribute name and column name in the database
                extra_info: dict = row[attribute_extra_info_column_name]
                for key, value in extra_info.items():
                    if key != "the_value":
                        # here we determine the name of columns
                        # with extra information about the value of
                        # the kleio attribute (group attribute or descendants)
                        # normally this would be comments or original wording
                        # of the_type or the_date.
                        # we need to use the name of the ORM attribute
                        # "type" or "date" instead of the column name
                        # and this is stored in "entity_attr_name" in
                        # the extra_info dict under the key for the column name.
                        attr_name = value.get("entity_attr_name", key)
                        xtra_col_name = f"{column_name}.{attr_name}"
                    else:
                        xtra_col_name = column_name
                    original = value.get("original", None)
                    if original is not None:
                        org_xtra_col_name = f"{xtra_col_name}.original"
                        extra_info_edits.append(
                            (row_number, org_xtra_col_name, original)
                        )
                    comment = value.get("comment", None)
                    if comment is not None:
                        cmt_xtra_col_name = f"{xtra_col_name}.comment"
                        extra_info_edits.append(
                            (row_number, cmt_xtra_col_name, comment)
                        )
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
            stmt = (
                select(
                    attr.c.entity.label("id"),
                    attr.c.the_value.label(column_name),
                    attr.c.the_date.label(date_column_name),
                    attr.c.aobs.label(obs_column_name),
                    attr.c.a_extra_info.label(extra_info_column_name),
                )
                .where(attr.c.the_type == mcol)
                .where(attr.c.entity.in_(df.index))
            )
            # col_names = stmt.columns.keys()

            with mysession as session:
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
                                if key != "the_value":
                                    attr_name = value.get("entity_attr_name", key)
                                    xtra_col_name2 = f"{column_name}.{attr_name}"
                                else:
                                    xtra_col_name2 = column_name
                                original = value.get("original", None)
                                if original is not None:
                                    org_xtra_col_name2 = f"{xtra_col_name2}.original"
                                    extra_info_edits.append(
                                        (row_number, org_xtra_col_name2, original)
                                    )
                                comment = value.get("comment", None)
                                if comment is not None:
                                    cmt_xtra_col_name2 = f"{xtra_col_name2}.comment"
                                    extra_info_edits.append(
                                        (row_number, cmt_xtra_col_name2, comment)
                                    )
                    for row_number, xtra_col_name2, avalue in extra_info_edits:
                        if xtra_col_name2 not in df2.columns:
                            df2[xtra_col_name2] = None
                        df2.iat[row_number, df2.columns.get_loc(xtra_col_name2)] = (
                            avalue
                        )

            if sql_echo:
                print(f"Query for more_attributes={mcol}:\n", stmt)

            if df2.empty or df2.iloc[0].count() == 0:
                df[mcol] = None  # nothing found we set the column to nulls
            else:
                df = df.join(df2)

    return df
