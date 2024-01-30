"""
Pandas related utilities for Timelink
In progress. Originally developped for the FAUC1537-1919 project
Now being integrated in the timelink-py package
"""
# Utilities for interacting with pandas
#
# IDEAS:
#    baptisms=function_to_df( function='n',
#                               act_tpe='bap',
#                               column_name='child', # instead of function
#                               person_info=True, # adds function_name, function_sex,
#                                                 #  columns
#                               dates_in=(after,before),
#                               name_like = name of person with function
#                               more_funcs=['pn','mn','ppn','mpn','pmn','mmn'],....)

import warnings
from sqlalchemy import not_, select
import pandas as pd

from timelink.api.database import TimelinkDatabase
from .name_to_df import pname_to_df  # noqa: F401
from .attribute_values import attribute_values  # noqa: F401

from IPython.display import display
from matplotlib import cm, colors

# TODO: move to separate files


def attribute_to_df(
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
    """Generate a pandas dataframe with people with a given attribute

    Args:
        the_type    : type of attribute, can have SQL wildcards, string
        column_name : a name for column receiving the attribute type, string
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
        Add : the_value_in: (list of values)
              the_value_between_inc (min, max, get >=min and <= max)
              the_value_between_exc (min, max, get >min and < max)

    """
    # We try to use an existing connection and table introspection
    # to avoid extra parameters and going to database too much
    dbsystem: TimelinkDatabase = db
    if dbsystem is None:
        raise (
            Exception(
                "db: TimelinkDatabase required. Must call timelink.api.database to set up a database connection"
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

            if df2.iloc[0].count() == 0:
                df[mcol] = None  # nothing found we set the column to nulls
            else:
                df = df.join(df2)

    return df


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
                "must call get_mhk_db(conn_string) to set up a database connection before or specify previously openned database with db="
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
        attr = db.get_model("attribute")
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


def p2rows(df, id1, id2):
    """Print two rows side by side, columns in lines

    Usefull to compare values
    """
    left_row = df.loc[[id1]].iloc[0]
    right_row = df.loc[[id2]].iloc[0]
    left = str(left_row).splitlines()
    right = str(right_row).splitlines()
    for i in range(0, min(len(left), len(right))):
        print(left[i], "|", right[i])
    print()


def category_palette(categories, cmap_name=None):
    """Create a color palette associated with a list of categories

    Args:
        Categories: List of categories
        cmap_name: matplotlib color map defaults to Pastel2
            see https://matplotlib.org/stable/tutorials/colors/colormaps.html

    Returns a dict with the categories as keys and colors as values
    """
    if cmap_name is None:
        cmap_name = "Pastel2"

    palette = cm.get_cmap(cmap_name, len(categories))
    mapcolors = [colors.rgb2hex(palette(i)) for i in range(len(categories))]
    cat_to_color = dict(zip(categories, mapcolors))
    return cat_to_color


def style_color_row_by_category(row, category="id", palette=None):
    """Color row by category. Function for styling dataframes
    Usage: display(df.style.apply(style_color_row_by_category,axis=1,palette=mypalette))
    Args
        row: this is passed by pandas when
        category:  column that determines the row color
        palette: a dict that maps category values to colors
    """
    id = row[category]
    row_colors = [f"background-color: {palette.get(id,'#ffffff')}"] * len(row)
    return row_colors


def styler_row_colors(df, category="id", columns=None, cmap_name="Pastel2"):
    """returns a dataframe setting the row color according to a category

    Args:
        df: dataframe
        category: name of column with category that determines color, defaults to id
        cmap_name; name of matplolib color map to use, defaults to 'Pastel2'

    """
    categories = df[category].unique()
    palette = category_palette(categories, cmap_name=cmap_name)
    if columns is None:
        columns = df.columns
    if category not in columns:
        cols = columns + [category]
    else:
        cols = columns

    r = df[cols].style.apply(
        style_color_row_by_category, axis=1, category=category, palette=palette
    )
    return r


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
        # the cols of persons are inserted automatically by attribute to df
        hcols_clean = [col for col in header_cols if col not in ["name", "sex", "obs"]]
    else:
        hcols_clean = header_cols
    header_df = attribute_to_df(
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
