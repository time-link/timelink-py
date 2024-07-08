""" Utilities for styling pandas dataframes"""
from matplotlib import colors
import matplotlib.pyplot as plt
import numpy as np


def category_palette(categories, cmap_name=None):
    """Create a color palette associated with a list of categories

    Args:
        Categories: List of categories
        cmap_name: matplotlib color map defaults to Pastel2
            see https://matplotlib.org/stable/tutorials/colors/colormaps.html

    Returns a dict with the categories as keys and colors as values
    """
    if cmap_name is None:
        cmap_name = "tab20"

    # Assuming 'cmap_name' is the name of your colormap and 'categories' is a list of categories
    num_categories = len(categories)
    cmap = plt.colormaps[cmap_name]
    palette = cmap(np.linspace(0, 1, num_categories))

    mapcolors = [colors.rgb2hex(palette[i]) for i in range(num_categories)]
    # shufle the colors
    # random.shuffle(mapcolors)

    cat_to_color = dict(zip(categories, mapcolors))
    return cat_to_color


def style_color_row_by_category(row, palette, category="id"):
    """Color row by category. Function for styling dataframes
    Usage: display(df.style.apply(style_color_row_by_category,axis=1,palette=mypalette))

    Args
        row: this is passed by pandas when rendering the dataframe
        palette: a dict that maps category values to colors
        category:  column that determines the row color
    """
    id = row[category]
    row_colors = [f"background-color: {palette.get(id,'#ffffff')}"] * len(row)
    return row_colors


def styler_row_colors(df, category="id", columns=None, palette=None, cmap_name=None):
    """returns a dataframe setting the row color according to a category

    Args:
        df: dataframe
        category: name of column with category that determines color, defaults to id
        cmap_name; name of matplolib color map to use, defaults to 'Pastel2'

    """
    categories = df[category].unique()
    if cmap_name is None:
        cmap_name = "Pastel2"
    if palette is None:
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
