"""test network generation"""

# pylint: disable=import-error
import pytest
import networkx as nx

from tests import TEST_DIR, skip_on_travis
from timelink.api.database import (
    TimelinkDatabase,
)
from timelink.kleio import KleioServer
from timelink.pandas import entities_with_attribute, attribute_values
from timelink.networks import network_from_attribute

# https://docs.pytest.org/en/latest/how-to/skipping.html
pytestmark = skip_on_travis
path_to_db_test_files = "sources/reference_sources/networks"
# only used for sqlite databases
db_path = f"{TEST_DIR}/sqlite/"
test_set = [("sqlite", "networks_db"), ("postgres", "networks_db")]


@pytest.fixture(scope="module")
def dbsystem(request):
    """Create a database for testing"""
    db_type, db_name = request.param

    database = TimelinkDatabase(db_name, db_type, db_path=db_path)

    # attach a kleio server
    kleio_server = KleioServer.start(kleio_home=f"{TEST_DIR}/timelink-home/projects/test-project")
    database.set_kleio_server(kleio_server)
    database.update_from_sources(path_to_db_test_files)
    try:
        yield database
    finally:
        database.drop_db()


@pytest.mark.parametrize("dbsystem", test_set, indirect=True)
def test_generate_network(dbsystem):
    """Test the generate_network method."""

    db = dbsystem
    # generate a network from the attribute "country"

    attribute_type = "wicky-viagem"
    attribute_values_list = attribute_values(
        attribute_type,
        db=db,
    )
    attribute_values_list.info()

    entities = entities_with_attribute(
        the_type=attribute_type,
        db=db,
    )
    if entities is not None:
        entities.info()

    network = network_from_attribute(
        attribute=attribute_type,
        mode="cliques",
        user="*none*",
        db=db,
    )

    assert isinstance(network, nx.Graph)
    assert len(network.nodes) > 0
