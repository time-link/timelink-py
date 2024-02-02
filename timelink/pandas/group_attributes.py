import warnings
from sqlalchemy import select, not_
import pandas as pd
from timelink.database import TimelinkDatabase

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


