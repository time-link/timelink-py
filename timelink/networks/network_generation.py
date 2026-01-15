"""Generation of networks"""

from itertools import combinations

import networkx as nx

from timelink.api.database import TimelinkDatabase
from timelink.api.models.entity import Entity
from timelink.kleio.utilities import convert_timelink_date as ctd
from timelink.kleio.utilities import format_timelink_date as ftd
from timelink.pandas import attribute_values, entities_with_attribute


def network_from_attribute(
    attribute: str,
    ignore_values: list[str] | None = None,
    mode="cliques",
    by_year=False,  # add year nodes between entities and values
    user=None,
    db: TimelinkDatabase | None = None,
    session=None,
) -> nx.Graph:
    """
    Generate a network from common attribute values.

    This function will generate a network connecting the entities
    that have the same value for the attribute given in the parameter.

    Args:
        attribute (str): The name (type) of the attribute used for generating the graph.
        ignore_values (list[str], optional): A list of values to ignore when generating the network.
                                              Defaults to None.
        mode (str, optional): The topology of the generated network (see bellow).
                              Valid values are "cliques" and "value-node". Defaults to "cliques".
        user (str, optional): Use real persons identified by this user. Defaults to "*none*".
        db (TimelinkDatase, optional): The TimelinkDatase object. Defaults to None.
                                       Either db or session must be provided.
        session (object, optional): The session object for the database connection. Defaults to None.

    Raises:
        None

    Topology the generated network:
        * If mode = "cliques" all the entities with attribute
          will be nodes in the graph and edges will be created between
          the entities with the same value of the attribute.
        * If mode = "value-node" a node will be created for each
          different value of the attribute a and edges will be
          created linking that node to the entities which have
          that value in attribute a.
        * In both cases entities with several values for the attribute
          contribute to the overall connectivity of the graph, by
          linking clusters of same value entities.

    Returns:
        networkx.classes.graph.Graph: The generated network as a networkx Graph object.

    Each node will have an associated dictionary of attributes:

        * "id": (entity id)
        * "type": "value_node" or entity class in the database.
        * "desc": a description of the node, automatically fetched
                  from the database (names of persons for instance)
        * "is_real": a flag stating if the "id" key refers to a real
                  entity or to an occurrence.
        * "url": a link to the entity information in the database
                 in the format http://localhost:8080/mhk/database/id/entityID

    Each edge will have associated the following key-value pairs:

        * "date1": date of the atribute in the left most node
        * "date2": date of the attribute in the right most node
        * "attribute": the type of the attribute
        * "value": the value of the attribute

    Examples:

    Generate a network of people that graduated in the same place
        ``G = network_from_attribute("graduated_at", mode="value-node")``

    """

    G = nx.Graph()
    if session is not None:
        mysession = session
    elif db is not None:
        mysession = db.session()
    else:
        raise ValueError(
            "No database nor session. Specifcy db=TimeLinkDatabase() or "
            "session=database session."
        )

    if ignore_values is None:
        ignore_values = ["?"]

    with mysession:
        attribute_values_list = attribute_values(
            the_type=attribute,
            db=db,
            session=mysession,
        )

        if attribute_values_list.empty:
            return G

        if ignore_values is not None:
            # remove the values to ignore
            attribute_values_list = attribute_values_list[
                ~attribute_values_list.index.isin(ignore_values)
            ]

        if attribute_values_list.empty:
            return G

        for avalue in attribute_values_list.index:
            # we get the date of the attribute
            date_col = f"{attribute}.date"
            # we get the obs of the attribute
            obs_col = f"{attribute}.obs"

            # we get the entities with that value
            entities = entities_with_attribute(
                the_type=attribute,
                the_value=avalue,
                db=db,
                session=mysession,
            )
            if entities is None or entities.empty:
                continue

            # in value node we create a node for each value
            if mode == "value-node":
                # in this mode we create a node for each value
                # and link it to the entities with that value§
                G.add_node(avalue, id=avalue, desc=avalue, type=attribute)

                for idx, row in entities.iterrows():
                    # get info on the entity
                    entity: Entity | None = mysession.get(Entity, idx)  # type: ignore

                    if entity is not None:
                        # Access the date_col and obs_col values
                        date_value = ftd(row[date_col]) if date_col in row else None
                        obs_value = row[obs_col] if obs_col in row else None
                        # add node for the entity
                        G.add_node(
                            idx,
                            desc=entity.description,
                            id=entity.id,
                            type=entity.pom_class,
                            group=entity.groupname,
                            date=date_value,
                            source=entity.the_source,
                        )
                        if by_year and date_value:
                            # add a year node if the date is not empty
                            year = ctd(date_value).year
                            G.add_node(year, type="year", desc=str(year))
                            # add an edge between the year and the entity
                            G.add_edge(year, idx, date=date_value, obs=obs_value)
                            # check if there is an edge between the value and the year
                            if not G.has_edge(avalue, year):
                                G.add_edge(avalue, year, date=date_value, obs=obs_value)
                        else:
                            G.add_edge(
                                avalue,
                                idx,
                                date=date_value,
                                attribute=attribute,
                                value=avalue,
                                obs=obs_value,
                            )
            elif mode == "cliques":
                # in this mode each entity with the same value is connected in a clique
                unique = entities.index.unique()
                for id in unique:
                    # add the entity nodes
                    # get info on the entity
                    entity: Entity | None = mysession.get(Entity, id)
                    if entity is not None:
                        G.add_node(
                            id,
                            desc=entity.description,
                            group=entity.groupname,
                            type=entity.pom_class,
                            source=entity.the_source,
                        )
                pairs = list(combinations(unique, 2))
                if len(pairs) > 1:
                    for id1, id2 in pairs:
                        # get the dates and obs
                        date1 = (
                            entities.at[id1, date_col]
                            if date_col in entities.columns
                            else ""
                        )
                        date2 = (
                            entities.at[id2, date_col]
                            if date_col in entities.columns
                            else ""
                        )
                        date1 = ftd(date1) if date1 else ""
                        date2 = ftd(date2) if date2 else ""
                        obs1: str = (
                            entities.at[id1, obs_col]
                            if obs_col in entities.columns
                            else ""
                        )
                        obs2: str = (
                            entities.at[id2, obs_col]
                            if obs_col in entities.columns
                            else ""
                        )
                        if ":" in date1:
                            date1 = f'"{date1}"'
                        if ":" in date2:
                            date2 = f'"{date2}"'
                        if ":" in obs1:
                            obs1 = f'"{obs1}"'
                        if ":" in obs2:
                            obs2 = f'"{obs2}"'

                        # add the edge
                        G.add_edge(
                            id1,
                            id2,
                            date1=date1,
                            date2=date2,
                            attribute=attribute,
                            value=avalue,
                            obs1=obs1,
                            obs2=obs2,
                        )
    return G
