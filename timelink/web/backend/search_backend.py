"""Database-native full-text search backends (decision D5).

Free-form search runs on the project's own database engine instead of
an external search server:

* **SQLite**: FTS5 with the ``trigram`` tokenizer (substring
  matching). Text is accent-folded and lower-cased at index time with
  :func:`timelink.linking.normalize.fold_text`, which doubles as the
  query-side normalizer.
* **PostgreSQL**: a ``tsvector`` column built with the ``portuguese``
  configuration over the folded text, queried with
  ``websearch_to_tsquery``; ``pg_trgm``-style substring fallback for
  short queries.

Solr is demoted to an optional backend behind a flag
(``TIMELINK_SEARCH_BACKEND=solr``); see ``solr_wrapper.py``.

All backends speak the same document shape as the Solr index did
(``id``, ``pom_class``, ``groupname``, ``name``, ``description``,
``searchable_field_t``) so page code and the indexing job do not
care which one is active.
"""
from abc import ABC, abstractmethod

from sqlalchemy import text as sql_text

from timelink.linking.normalize import fold_text


class SearchBackend(ABC):
    """Common interface for entity full-text search."""

    # entity classes excluded from the index (metadata rows)
    IGNORE_CLASSES = ("class", "rentity", "source")

    def __init__(self, engine):
        self.engine = engine

    @abstractmethod
    def setup(self):
        """Create index structures if missing."""

    @abstractmethod
    def index_entities(self, docs: list[dict]):
        """Add/replace documents. See entity_to_doc for the shape."""

    @abstractmethod
    def search(self, query: str, limit: int = 50) -> list[dict]:
        """Return matching documents (same keys as indexed)."""

    @abstractmethod
    def delete_entity(self, entity_id: str):
        """Remove one document (entity deleted/renamed)."""

    @abstractmethod
    def health_check(self) -> bool:
        """True if the backend is usable."""

    @staticmethod
    def entity_to_doc(entity_data: dict) -> dict:
        """Build the backend document from an EntityAttrRelSchema dump.

        Same field extraction the Solr wrapper used: values from the
        searchable keys plus the entity's own name/description, folded
        into one text field.
        """
        searchable_keys = (
            "inside", "the_source", "the_value", "obs",
            "org_name", "dest_name", "the_type", "name", "description",
        )
        parts = {entity_data.get(key) for key in searchable_keys
                 if isinstance(entity_data.get(key), str) and entity_data.get(key)}

        def walk(container):
            if isinstance(container, dict):
                for key, value in container.items():
                    if key in searchable_keys and isinstance(value, str) and value:
                        parts.add(value)
                    elif key in ("rels_in", "rels_out", "contains",
                                 "attributes", "links", "extra_info"):
                        walk(value)
            elif isinstance(container, list):
                for item in container:
                    walk(item)

        walk({k: entity_data.get(k) for k in
              ("rels_in", "rels_out", "contains", "attributes", "links", "extra_info")})

        name = entity_data.get("name") or ""
        description = entity_data.get("description") or ""
        for value in (name, description):
            if value:
                parts.add(value)

        clean_parts = [p for p in parts if p and not p.isspace()]
        return {
            "id": entity_data["id"],
            "pom_class": entity_data.get("pom_class", ""),
            "groupname": entity_data.get("groupname", ""),
            "name": name,
            "description": description,
            "searchable_field_t": fold_text(" ".join(clean_parts)),
        }


class SQLiteFTSBackend(SearchBackend):
    """FTS5 backend for SQLite projects (trigram tokenizer).

    Requires SQLite >= 3.34 (trigram tokenizer). Text is stored
    already accent-folded and lower-cased; queries are folded the
    same way, so diacritic-insensitive matching works.
    """

    TABLE = "entity_fts"

    def __init__(self, engine):
        super().__init__(engine)
        self._fts5_available = None

    def _check_fts5(self) -> bool:
        if self._fts5_available is None:
            try:
                with self.engine.connect() as conn:
                    conn.execute(sql_text("CREATE VIRTUAL TABLE IF NOT EXISTS fts5_probe USING fts5(probe)"))
                    conn.execute(sql_text("DROP TABLE IF EXISTS fts5_probe"))
                self._fts5_available = True
            except Exception as e:
                print(f"FTS5 not available in this SQLite build: {e}")
                self._fts5_available = False
        return self._fts5_available

    def setup(self):
        if not self._check_fts5():
            return
        with self.engine.begin() as conn:
            conn.execute(sql_text(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {self.TABLE} USING fts5(
                    id UNINDEXED,
                    pom_class UNINDEXED,
                    groupname UNINDEXED,
                    name,
                    description,
                    searchable_field_t,
                    tokenize = 'trigram'
                )
            """))

    def index_entities(self, docs: list[dict]):
        if not docs or not self._check_fts5():
            return
        with self.engine.begin() as conn:
            for doc in docs:
                conn.execute(sql_text(f"DELETE FROM {self.TABLE} WHERE id = :id"),
                             {"id": doc["id"]})
                conn.execute(sql_text(f"""
                    INSERT INTO {self.TABLE}
                        (id, pom_class, groupname, name, description, searchable_field_t)
                    VALUES
                        (:id, :pom_class, :groupname, :name, :description, :searchable_field_t)
                """), doc)

    def search(self, query: str, limit: int = 50) -> list[dict]:
        if not query or not query.strip() or not self._check_fts5():
            return []
        words = fold_text(query).split()
        with self.engine.connect() as conn:
            if all(len(w) >= 3 for w in words):
                # trigram substring matching via MATCH; prefix '*' per word
                match_expr = " ".join(f'"{w}"*' for w in words)
                rows = conn.execute(sql_text(f"""
                    SELECT id, pom_class, groupname, name, description
                    FROM {self.TABLE}
                    WHERE {self.TABLE} MATCH :match
                    LIMIT :limit
                """), {"match": match_expr, "limit": limit}).mappings().all()
            else:
                # short words: LIKE fallback over the folded text
                where = " AND ".join(
                    f"searchable_field_t LIKE :w{i}" for i in range(len(words)))
                params = {"limit": limit}
                params.update({f"w{i}": f"%{w}%" for i, w in enumerate(words)})
                rows = conn.execute(sql_text(f"""
                    SELECT id, pom_class, groupname, name, description
                    FROM {self.TABLE}
                    WHERE {where}
                    LIMIT :limit
                """), params).mappings().all()
        return [dict(row) for row in rows]

    def delete_entity(self, entity_id: str):
        if not self._check_fts5():
            return
        with self.engine.begin() as conn:
            conn.execute(sql_text(f"DELETE FROM {self.TABLE} WHERE id = :id"),
                         {"id": entity_id})

    def count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                sql_text(f"SELECT count(*) FROM {self.TABLE}")).scalar_one()

    def health_check(self) -> bool:
        return self._check_fts5()


class PostgresFTSBackend(SearchBackend):
    """PostgreSQL full-text backend.

    A ``entity_fts`` table holds one row per entity; ``tsv`` is built
    with ``to_tsvector('portuguese', ...)`` over the accent-folded
    text at index time (no generated column: ``unaccent`` is not
    immutable). Queries use ``websearch_to_tsquery``; terms shorter
    than 3 characters fall back to trigram/LIKE matching.
    """

    TABLE = "entity_fts"

    def setup(self):
        with self.engine.begin() as conn:
            conn.execute(sql_text(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id VARCHAR(64) PRIMARY KEY,
                    pom_class VARCHAR(64),
                    groupname VARCHAR(64),
                    name VARCHAR(254),
                    description VARCHAR(4096),
                    searchable_field_t TEXT,
                    tsv TSVECTOR
                )
            """))
            conn.execute(sql_text(
                f"CREATE INDEX IF NOT EXISTS entity_fts_tsv_idx "
                f"ON {self.TABLE} USING GIN (tsv)"))

    def index_entities(self, docs: list[dict]):
        if not docs:
            return
        with self.engine.begin() as conn:
            for doc in docs:
                conn.execute(sql_text(f"""
                    INSERT INTO {self.TABLE}
                        (id, pom_class, groupname, name, description,
                         searchable_field_t, tsv)
                    VALUES
                        (:id, :pom_class, :groupname, :name, :description,
                         :searchable_field_t,
                         to_tsvector('portuguese',
                                     coalesce(:searchable_field_t, ''))
                             || to_tsvector('portuguese',
                                            coalesce(:name, '') || ' '
                                            || coalesce(:description, ''))
                             || to_tsvector('simple', :id))
                    ON CONFLICT (id) DO UPDATE SET
                        pom_class = EXCLUDED.pom_class,
                        groupname = EXCLUDED.groupname,
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        searchable_field_t = EXCLUDED.searchable_field_t,
                        tsv = EXCLUDED.tsv
                """), doc)

    def search(self, query: str, limit: int = 50) -> list[dict]:
        if not query or not query.strip():
            return []
        words = fold_text(query).split()
        with self.engine.connect() as conn:
            if all(len(w) >= 3 for w in words):
                rows = conn.execute(sql_text(f"""
                    SELECT id, pom_class, groupname, name, description
                    FROM {self.TABLE}
                    WHERE tsv @@ websearch_to_tsquery('portuguese', :query)
                    ORDER BY ts_rank(tsv,
                             websearch_to_tsquery('portuguese', :query)) DESC
                    LIMIT :limit
                """), {"query": " ".join(words), "limit": limit}).mappings().all()
            else:
                where = " AND ".join(
                    f"searchable_field_t LIKE :w{i}" for i in range(len(words)))
                params = {"limit": limit}
                params.update({f"w{i}": f"%{w}%" for i, w in enumerate(words)})
                rows = conn.execute(sql_text(f"""
                    SELECT id, pom_class, groupname, name, description
                    FROM {self.TABLE}
                    WHERE {where}
                    LIMIT :limit
                """), params).mappings().all()
        return [dict(row) for row in rows]

    def delete_entity(self, entity_id: str):
        with self.engine.begin() as conn:
            conn.execute(sql_text(f"DELETE FROM {self.TABLE} WHERE id = :id"),
                         {"id": entity_id})

    def count(self) -> int:
        with self.engine.connect() as conn:
            return conn.execute(
                sql_text(f"SELECT count(*) FROM {self.TABLE}")).scalar_one()

    def health_check(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(sql_text("SELECT 1"))
            return True
        except Exception:
            return False


def create_search_backend(db_type: str, engine, solr_manager=None) -> SearchBackend:
    """Backend selection follows the project's database type (D5).

    ``solr_manager`` selects the legacy Solr wrapper (its container
    setup is the caller's responsibility); otherwise the backend
    matches the database engine.
    """
    if solr_manager is not None:
        return SolrBackend(solr_manager)
    if db_type == "postgres":
        return PostgresFTSBackend(engine)
    return SQLiteFTSBackend(engine)


class SolrBackend(SearchBackend):
    """Adapter delegating to the legacy Solr wrapper.

    Selected with ``TIMELINK_SEARCH_BACKEND=solr``; kept until the
    Solr code is removed after one release without use (D5).
    """

    def __init__(self, solr_manager):
        super().__init__(engine=None)
        self.solr_manager = solr_manager

    def setup(self):
        # container + client setup is SolrWrapper's job, done by the caller
        pass

    def index_entities(self, docs: list[dict]):
        self.solr_manager.solr_client.add(docs, commit=True)

    def search(self, query: str, limit: int = 50) -> list[dict]:
        results = self.solr_manager.solr_client.search(
            q=f"searchable_field_t:*{query}*")
        return [
            {
                "id": result.get("id"),
                "pom_class": result.get("pom_class", ""),
                "groupname": result.get("groupname", ""),
                "name": result.get("name", ""),
                "description": result.get("description", ""),
            }
            for result in results
        ]

    def delete_entity(self, entity_id: str):
        self.solr_manager.solr_client.delete(id=entity_id)

    def health_check(self) -> bool:
        try:
            self.solr_manager.health_check()
            return True
        except Exception:
            return False
