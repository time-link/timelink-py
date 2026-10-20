import pytest
from unittest.mock import MagicMock, patch
from timelink.web.backend.solr_wrapper import SolrWrapper


def test_setup_solr_container_already_running():
    w = SolrWrapper()

    with patch("subprocess.run") as run:
        run.return_value.stdout = w.solr_container_name
        w.setup_solr_container()
        run.assert_called_once()


def test_setup_solr_container_exists_but_stopped():
    w = SolrWrapper()

    with patch("subprocess.run") as run:
        run.side_effect = [
            MagicMock(stdout=""),
            MagicMock(stdout=w.solr_container_name),
            MagicMock()
        ]
        w.setup_solr_container()
        assert run.call_args_list[2][0][0][0:2] == ["docker", "start"]


def test_setup_solr_container_new_container():
    w = SolrWrapper()

    with patch("subprocess.run") as run:
        run.side_effect = [
            MagicMock(stdout=""),
            MagicMock(stdout=""),
            MagicMock()
        ]
        w.setup_solr_container()
        assert "run" in run.call_args_list[-1][0][0]


def test_init_solr_client():
    w = SolrWrapper()
    with patch("pysolr.Solr") as solr:
        w.init_solr_client()
        solr.assert_called_once()


def test_health_check():
    w = SolrWrapper()
    mock = MagicMock()
    mock.ping.return_value = '{"status":"OK"}'
    w.solr_client = mock
    w.health_check()
    mock.ping.assert_called_once()


def test_entity_to_solr_doc():
    w = SolrWrapper()
    data = {
        "id": "1",
        "pom_class": "P",
        "groupname": "G",
        "inside": "A",
        "the_order": 1,
        "the_level": 2,
        "updated": None,
        "the_source": "SRC",
        "rels_in": [{"obs": "hello"}],
    }
    doc = w.entity_to_solr_doc(data)
    assert doc["id"] == "1"
    assert "hello" in doc["searchable_field_t"]


def test_wait_for_solr_ok():
    w = SolrWrapper()
    with patch("requests.get") as r:
        r.return_value.status_code = 200
        assert w.wait_for_solr(8983)


def test_wait_for_solr_timeout():
    w = SolrWrapper()
    with patch("requests.get", side_effect=Exception):
        with pytest.raises(RuntimeError):
            w.wait_for_solr(8983, timeout=1)


def test_switch_active_core_existing():
    w = SolrWrapper()
    with patch.object(w, "wait_for_solr"), \
         patch("requests.get") as r, \
         patch("pysolr.Solr") as solr:

        r.return_value.json.return_value = {"status": {"foo": {}}}
        w.switch_active_core("foo")
        solr.assert_called_once()


def test_switch_active_core_create():
    w = SolrWrapper()
    with patch.object(w, "wait_for_solr"), \
         patch("requests.get") as r, \
         patch("subprocess.run") as run, \
         patch("pysolr.Solr"):

        r.return_value.json.return_value = {"status": {}}
        w.switch_active_core("newcore")
        run.assert_called()
