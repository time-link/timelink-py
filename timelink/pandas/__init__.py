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
from .entities_with_attribute import entities_with_attribute  # noqa: F401
from .attribute_values import attribute_values  # noqa: F401

from IPython.display import display
from matplotlib import cm, colors

# TODO: move to separate files



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

