""" Generation of networks

TODO: pass DB object instead of Engine
"""
from itertools import combinations
import networkx as nx
from sqlalchemy import text


def network_from_attribute(engine, a: str, mode="cliques", user="*none*"):
    """Generate a network from common attribute values.

    This function will generate a network connecting the
    entities that have the same value for the
    attribute given in the parameter.

    Parameters
    ----------
    engine : sqlalchemy Engine
        An SQLAlchemy engine connected to the target database.
    a : str
        The name (type) of the attribute used for generating the graph.
    user: str  use real persons identified by this user (optional).
    mode : {"cliques", "value-node"}, optional (default="cliques")
        The topology the generated network.

        If mode = "cliques" all the entities with attribute `a` will be
        nodes in the graph and edges will be created between the entities with the same
        value of the attribute.

        If mode = "value-node" a node will be created for each different
        value of the attribute `a` and edges will be created linking that node
        to the entities which have that value in attribute `a`.
        In both cases entities with several values for the attribute contribute to the
        overall connectivity of the graph, by linking clusters of same value entities.

    Returns
    -------
    networkx Graph (networkx.classes.graph.Graph)
        Each node will have an associated dictionary of attributes
            "id" (entity id)
            "type" "value_node" or entity class in the database.
            "desc" a description of the node, automatically fetched
                from the database (names of persons for instance)
            "is_real" a flag stating if the "id" key refers to a real
            entity or to an occurrence.
            "url" a link to the entity information in the database
                inf the format http://localhost:8080/mhk/database/id/entityID
        Each edge will have associated the following key-value pairs
            "date1" date of the atribute in the left most node
            "date2" date of the attribute in the right most node
            "attribute" the type of the attribute
            "value" the value of the attribute

    Examples
    --------

        G = network_from_attribute(e, "graduated_at", mode="value-node")

    """

    sql = "select distinct the_value from attributes where the_type = :the_type and the_value <> '?'"
    G = nx.Graph()
    with engine.connect() as conn:
        result = conn.execute(text(sql), [{"the_type": a}])
        values = result.all()
        for (avalue,) in values:
            if user == "*none*":
                sql = "select id,name,the_date from nattributes where the_type=:the_type and the_value = :the_value"
            else:
                sql = "SELECT IFNULL( (select rid from rlinks where instance=n.id and user=:user),id) as id, name, the_date  from nattributes n where the_type=:the_type and the_value = :the_value"
            # TODO also fetch the instance SELECT IFNULL( (select rid from rlinks where instance=n.id and user=:user),id) as id, id as instance, name,...
            # TODO then test if id=instance. If not add attribute to node is_real=yes otherwise "no"
            # TODO do the same with the first select.
            # TODO add to nodes a url attribute if host and dbase are present is present https://joaquims-mbpr.local/mhk/toliveira/id/rp-1
            result = conn.execute(
                text(sql), [{"the_type": a, "the_value": avalue, "user": user}]
            )
            entities = result.all()

            if mode == "value-node":
                G.add_node(avalue, desc=avalue, type=a)
                for id, name, date in entities:
                    G.add_node(id, desc=name, type="person")
                    G.add_edge(
                        avalue, id, date1=date, date2=date, attribute=a, value=avalue
                    )
            elif len(entities) > 1:
                for id, name, _date in entities:
                    G.add_node(
                        id, desc=name, type="person"
                    )  # this should come from the entity class
                pairs = list(combinations(entities, 2))
                # TODO: optional date range filtering
                for (e1, _n1, d1), (e2, _n1, d2) in pairs:
                    G.add_edges_from(
                        [
                            (
                                e1,
                                e2,
                                {
                                    "date1": d1,
                                    "date2": d2,
                                    "attribute": a,
                                    "value": avalue,
                                },
                            )
                        ]
                    )
    return G
