""" Return the attributes of a group of entities in a dataframe."""

import warnings
from sqlalchemy import column, select, not_
from sqlalchemy.orm.session import Session
import pandas as pd
from IPython.display import display
from timelink.api.database import TimelinkDatabase
from timelink.pandas.entities_with_attribute import entities_with_attribute
from timelink.pandas.styles import category_palette, styler_row_colors


def group_attributes(
    group: list,
    entity_type="entity",
    include_attributes=None,
    exclude_attributes=None,
    show_elements=None,
    db: TimelinkDatabase = None,
    session: Session = None,
    sql_echo=False,
):
    """Return the attributes of a group of entities in a dataframe.

    Args:
    group: list of ids
    entity_type: type of entities to show
    show_elements: elements of entity type to include
                (e.g. name, description, obs)
    include_attributes: list of attribute types to include
    exclude_attributes: list of attribute types to exclude
    db: a TimelinkDatabase object if None specify session
    session: a sqlalchemy session object, if None specify db
    sql_echo: if True echo the sql generated

    """

    if group is None:
        group = []
        warnings.warn("No list of ids specified", stacklevel=2)
        return None

    mysession = None
    dbsystem: TimelinkDatabase = None
    if db is not None:
        dbsystem = db
        mysession = dbsystem.session()
    elif session is not None:
        mysession = session
    else:
        raise (
            Exception(
                "must call TimelinkDatabase() and pass db= "
                "or specify previously openned session with session="
            )
        )

    entity_types = db.get_models_ids()
    if entity_type not in entity_types:
        raise ValueError(f"entity_type must be one of {entity_types}")

    entity_model = db.get_model(entity_type)
    # get the columns of the entity table, check if more_info is valid
    # we need the "select" to get all the columns up in the inheritance
    id_col: column = select(entity_model).selected_columns["id"]
    entity_names = select(entity_model).selected_columns.keys()
    if show_elements is None:
        show_elements = []

    cols = [id_col]
    extra_cols = []
    # collect the column objects for the select list
    for mi in show_elements:
        if mi not in entity_names:
            raise ValueError(
                f"{mi} is not a valid column for {entity_type}."
                " Use entity_type arg to specify the desired entity type (e.g. person)."
            )
        else:
            extra_cols.append(select(entity_model).selected_columns[mi])

    cols.extend(extra_cols)

    attr = db.get_table("attribute")

    cols.extend(
        [
            attr.c.the_type,
            attr.c.the_value,
            attr.c.the_date,
            attr.c.obs.label("attr_obs"),
        ]
    )

    select_entities = select(entity_model).where(id_col.in_(group))

    stmt = select_entities.join(
        attr, attr.c.entity == entity_model.id, isouter=True
    ).with_only_columns(*cols)

    # these should allow sql wild cards
    # but it is not easy in sql
    if include_attributes is not None and len(include_attributes) != 0:
        stmt = stmt.where(attr.c.the_type.in_(include_attributes))
    if exclude_attributes is not None and len(exclude_attributes) != 0:
        stmt = stmt.where(not_(attr.c.the_type.in_(exclude_attributes)))

    if sql_echo:
        print(stmt)

    with mysession as session:
        records = session.execute(stmt)
        col_names = stmt.selected_columns.keys()
        df = pd.DataFrame.from_records(records, index="id", columns=col_names)
    return df


def display_group_attributes(
    ids,
    entity_type="entity",
    header_elements=None,
    header_attributes=None,
    sort_header=None,
    sort_attributes=None,
    # These go to de_row_colors
    category="id",
    cmap_name="tab20",
    # these go to group_attributes
    include_attributes=None,
    exclude_attributes=None,
    db: TimelinkDatabase = None,
):
    """Display attributes of a group with header and colored rows.

    Same as group attributes but a header is displayed for each entity
    and each entity is colored. The attribute list is also colored,
    to make is clear which attributes are from which entity.

    Args:
        ids: list of ids
        entity_type: type of entities to show
        header_elements: elements of entity type to include in header
                    (e.g. name, description, obs)
        header_attributes: list of attribute types to include in header
        sort_header: sort the header by this attribute
        sort_attributes: sort the attributes by this attribute
        include_attributes: list of attribute types to include
        exclude_attributes: list of attribute types to exclude
        db: a TimelinkDatabase object if None specify session
        category: column to use for coloring
        cmap_name: name of the colormap to use.
                    See https://matplotlib.org/stable/tutorials/colors/colormaps.html

    """

    if header_elements is None:
        header_elements = []
    if header_attributes is None:
        header_attributes = ["%"]
        column_name = "the_type"
    else:
        column_name = header_attributes[0]

    table_cols = ["the_type", "the_value", "the_date", "attr_obs"]

    header_df = entities_with_attribute(
        header_attributes[0],
        entity_type=entity_type,
        column_name=column_name,
        show_elements=header_elements,
        more_attributes=header_attributes[1:],
        filter_by=ids,
        db=db,
    )
    # remove  entries with duplicate index from header_df

    header_df = (
        header_df.reset_index()
        .drop_duplicates(subset="id", keep="first")
        .set_index("id")
    )

    if sort_header is not None:
        header_df.sort_values(sort_header, inplace=True)

    header_df["id"] = header_df.index
    header_df.reset_index(drop=True, inplace=True)
    header_cols = header_df.columns.tolist()
    if category not in header_cols:
        header_cols = [category] + header_cols

    categories = header_df[category].unique()
    palette = category_palette(categories, cmap_name=cmap_name)

    header_df = styler_row_colors(
        header_df[header_cols], category=category, palette=palette)
    display(header_df)

    df = group_attributes(
        ids,
        entity_type=entity_type,
        show_elements=header_elements,
        include_attributes=include_attributes,
        exclude_attributes=exclude_attributes,
        db=db,
    )
    if sort_attributes is not None:
        df.sort_values(sort_attributes, inplace=True)
    df["id"] = df.index
    df.reset_index(drop=True, inplace=True)
    table_cols = df.columns.tolist()
    if category not in table_cols:
        table_cols = [category] + table_cols
    df = styler_row_colors(df[table_cols], category="id", palette=palette)
    display(df)
