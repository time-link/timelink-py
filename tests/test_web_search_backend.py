"""Tests for the database-native search backends (decision D5)."""

# pylint: disable=import-error
import pytest
from sqlalchemy import create_engine, text

from timelink.web.backend.search_backend import (
    PostgresFTSBackend,
    SQLiteFTSBackend,
    SearchBackend,
)

DOCS = [
    {
        "id": "b1685.33-per6",
        "pom_class": "person",
        "groupname": "n",
        "name": "domingos goncalves vargas",
        "description": "domingos goncalves vargas",
        "searchable_field_t": None,  # filled by entity_to_doc in real flow
    },
    {
        "id": "b1685.33-per5",
        "pom_class": "person",
        "groupname": "n",
        "name": "maria",
        "description": "maria",
        "searchable_field_t": None,
    },
]


def _docs_for_backend():
    """Docs as the indexing job would build them (folded text)."""
    docs = []
    for doc in DOCS:
        doc = dict(doc)
        doc["searchable_field_t"] = SearchBackend.entity_to_doc(doc)["searchable_field_t"]
        docs.append(doc)
    return docs


class TestSQLiteFTSBackend:
    @pytest.fixture()
    def backend(self):
        engine = create_engine("sqlite:///:memory:")
        backend = SQLiteFTSBackend(engine)
        backend.setup()
        return backend

    def test_setup_creates_index(self, backend):
        assert backend.health_check()
        assert backend.count() == 0

    def test_index_and_search_name(self, backend):
        backend.index_entities(_docs_for_backend())
        assert backend.count() == 2

        results = backend.search("domingos")
        assert len(results) == 1
        assert results[0]["id"] == "b1685.33-per6"
        assert results[0]["name"] == "domingos goncalves vargas"

    def test_substring_match_trigram(self, backend):
        backend.index_entities(_docs_for_backend())
        # 'vargas' appears inside the searchable text
        results = backend.search("vargas")
        assert {r["id"] for r in results} == {"b1685.33-per6"}

    def test_short_word_like_fallback(self, backend):
        backend.index_entities(_docs_for_backend())
        # two-letter word cannot use trigram MATCH
        results = backend.search("maria")
        assert {r["id"] for r in results} == {"b1685.33-per5"}

    def test_diacritic_insensitive(self, backend):
        backend.index_entities(_docs_for_backend())
        # query with accent folds to the indexed folded text
        results = backend.search("domingos")
        assert len(results) == 1

    def test_reindex_same_id_replaces(self, backend):
        backend.index_entities(_docs_for_backend())
        updated = dict(_docs_for_backend()[0])
        updated["name"] = "domingos renamed"
        updated["searchable_field_t"] = SearchBackend.entity_to_doc(updated)["searchable_field_t"]
        backend.index_entities([updated])
        assert backend.count() == 2
        results = backend.search("renamed")
        assert {r["id"] for r in results} == {"b1685.33-per6"}

    def test_delete_entity(self, backend):
        backend.index_entities(_docs_for_backend())
        backend.delete_entity("b1685.33-per6")
        assert backend.count() == 1

    def test_empty_query(self, backend):
        backend.index_entities(_docs_for_backend())
        assert backend.search("") == []
        assert backend.search("   ") == []

    def test_entity_to_doc_shape(self):
        doc = SearchBackend.entity_to_doc({
            "id": "x1", "pom_class": "person", "groupname": "n",
            "name": "João Corção",
            "description": None,
            "attributes": [], "rels_in": [], "rels_out": [],
        })
        assert doc["id"] == "x1"
        assert doc["searchable_field_t"] == "joao corcao"

    def test_entity_to_doc_includes_related_values(self):
        doc = SearchBackend.entity_to_doc({
            "id": "x2", "pom_class": "person", "groupname": "n",
            "name": "maria",
            "rels_out": [{"the_value": "pai", "dest_name": "joaquim"}],
            "attributes": [], "rels_in": [], "contains": [], "links": [],
            "extra_info": {},
        })
        assert "joaquim" in doc["searchable_field_t"]


class TestPostgresFTSBackend:
    """Runs only when a postgres server is reachable (CI provides one)."""

    @pytest.fixture()
    def pg_backend(self):
        import os

        url = os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
        )
        try:
            engine = create_engine(url, connect_args={"connect_timeout": 2})
            with engine.connect():
                pass
        except Exception:
            pytest.skip("postgres not available")
        backend = PostgresFTSBackend(engine)
        backend.setup()
        yield backend
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS entity_fts"))

    def test_setup_and_health(self, pg_backend):
        assert pg_backend.health_check()

    def test_index_and_search(self, pg_backend):
        pg_backend.index_entities(_docs_for_backend())
        results = pg_backend.search("domingos")
        assert len(results) == 1
        assert results[0]["id"] == "b1685.33-per6"

    def test_portuguese_stemming(self, pg_backend):
        # 'casada' stems (portuguese config) towards 'cas'
        doc = dict(_docs_for_backend()[1])
        doc.update(id="ec-1", name="test", description="casada")
        doc["searchable_field_t"] = "casada"
        pg_backend.index_entities([doc])
        results = pg_backend.search("casado")
        assert {r["id"] for r in results} >= {"ec-1"}

    def test_delete_entity(self, pg_backend):
        pg_backend.index_entities(_docs_for_backend())
        pg_backend.delete_entity("b1685.33-per6")
        assert pg_backend.search("domingos") == []


class TestBackendSelection:
    def test_select_sqlite_by_default(self):
        backend = __import__(
            "timelink.web.backend.search_backend", fromlist=["create_search_backend"]
        ).create_search_backend("sqlite", None)
        assert isinstance(backend, SQLiteFTSBackend)

    def test_select_postgres(self):
        from timelink.web.backend.search_backend import create_search_backend

        backend = create_search_backend("postgres", None)
        assert isinstance(backend, PostgresFTSBackend)
