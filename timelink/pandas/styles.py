""" Utilities for styling pandas dataframes"""

from matplotlib import cm, colors


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
