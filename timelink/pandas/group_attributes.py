import warnings
from sqlalchemy import select, not_
import pandas as pd
from IPython.display import display

from timelink.api.database import TimelinkDatabase


from timelink.pandas import entities_with_attribute
from timelink.pandas.styles import styler_row_colors


def group_attributes(
    group: list,
    include_attributes=None,
    exclude_attributes=None,
    person_info=True,
    db: TimelinkDatabase = None,
    sql_echo=False,
):
    """Return the attributes of a group of people in a dataframe.

    Args:
    group: list of ids
    include_attributes: list of attribute types to include
    exclude_attributes: list of attribute types to exclude
    person_info: include person information (name, sex, obs)
    db: a TimelinkDatabase object
    sql_echo: if True echo the sql generated

    """

    if group is None:
        group = []
        warnings.warn("No list of ids specified", stacklevel=2)
        return None

    dbsystem: TimelinkDatabase = None
    if db is not None:
        dbsystem = db
    else:
        raise (
            Exception(
                "must call get_mhk_db(conn_string) to set up a database connection before "
                "or specify previously openned database with db="
            )
        )

    if person_info:  # to fetch person info we need nattributes view
        attr = db.get_nattribute_view()
        id_col = attr.c.id
        stmt = select(
            attr.c.id,
            attr.c.name.label("name"),
            attr.c.sex.label("sex"),
            attr.c.pobs.label("person_obs"),
            attr.c.the_type,
            attr.c.the_value,
            attr.c.the_date,
            attr.c.aobs.label("attr_obs"),
        )
        cols = ["id", "name", "sex", "persons_obs", "type", "value", "date", "attr_obs"]
    else:  # no person information required we use the attributes table
        attr_model = db.get_model("attribute")
        attr = attr_model.__table__
        id_col = attr.c.entity
        stmt = select(
            attr.c.entity,
            attr.c.the_type,
            attr.c.the_value,
            attr.c.the_date,
            attr.c.obs.label("attr_obs"),
        )
        cols = ["id", "type", "value", "date", "attr_obs"]

    stmt = stmt.where(id_col.in_(group))

    # these should allow sql wild cards
    # but it is not easy in sql
    if include_attributes is not None:
        stmt = stmt.where(attr.c.the_type.in_(include_attributes))
    if exclude_attributes is not None:
        stmt = stmt.where(not_(attr.c.the_type.in_(exclude_attributes)))

    if sql_echo:
        print(stmt)

    with dbsystem.session() as session:
        records = session.execute(stmt)
        df = pd.DataFrame.from_records(records, index=["id"], columns=cols)

    return df


def display_group_attributes(
    ids,
    header_cols=None,
    sort_header=None,
    table_cols=None,
    sort_attributes=None,
    # These go to de_row_colors
    category="id",
    cmap_name="Pastel2",
    # these go to group attributes
    include_attributes=None,
    exclude_attributes=None,
    person_info=True,
    db: TimelinkDatabase = None,
):
    """Display attributes of a group with header and colored rows"""

    if header_cols is None:
        header_cols = []
    if table_cols is None:
        table_cols = ["type", "value", "date", "attr_obs"]

    if person_info is True:
        # the cols of persons are inserted automatically by entities_with_attribute
        hcols_clean = [col for col in header_cols if col not in ["name", "sex", "obs"]]
    else:
        hcols_clean = header_cols

    header_df = entities_with_attribute(
        hcols_clean[0],
        person_info=person_info,
        more_cols=hcols_clean[1:],
        filter_by=ids,
        db=db,
    )
    if sort_header is not None:
        header_df.sort_values(sort_header, inplace=True)

    header_df["id"] = header_df.index
    header_df.reset_index(drop=True, inplace=True)
    if category not in header_cols:
        header_cols = [category] + header_cols
    header_df = styler_row_colors(
        header_df[header_cols], category=category, cmap_name=cmap_name
    )
    display(header_df)

    df = group_attributes(
        ids,
        include_attributes=include_attributes,
        exclude_attributes=exclude_attributes,
        person_info=False,
        db=db,
    )
    if sort_attributes is not None:
        df.sort_values(sort_attributes, inplace=True)
    df["id"] = df.index
    df.reset_index(drop=True, inplace=True)
    if category not in table_cols:
        table_cols = [category] + table_cols
    df = styler_row_colors(df[table_cols], category="id", cmap_name=cmap_name)
    display(df)
