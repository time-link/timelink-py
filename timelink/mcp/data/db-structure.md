# Timelink database structure — reference for agents (draft)

Packaged copy served as the MCP resource `timelink://schema/{database}`.
The editable source is `docs/mcp-db-structure-draft.md` — update it there
and copy it here (`cp docs/mcp-db-structure-draft.md
timelink/mcp/data/db-structure.md`).

Companion to `docs/mcp-tools-draft.md`. This is the schema description an
agent receives (as an MCP resource and summarized in
`timelink/mcp/AGENTS.md`). It describes the *conceptual model first*, then
the tables and views an agent can actually query, then the conventions
that are easy to get wrong, and finally query recipes mapped to the tools.

Source of truth: `timelink/api/models/*.py`, `timelink/api/database_views.py`.

---

## 1. Mental model

1. **Everything is an entity.** Every person, act, source, object, relation
   and attribute has one row in the `entities` table with a unique string
   `id`. Class-specific data lives in *specialization tables*
   (`persons`, `acts`, ...) sharing the same `id` (joined-table
   inheritance). The entity's class is in `entities.class` (a.k.a.
   `pom_class`); it determines which specialization table completes it.
2. **Attributes are data about one entity** (`attributes` table): a
   `the_type` / `the_value` / `the_date` triple plus provenance. Think
   "property with citation", e.g. type `naturalidade`, value `Soure`,
   date `16010230`.
3. **Relations connect two entities** (`relations` table): origin →
   destination with `the_type` / `the_value` / `the_date`. Participation
   in an act is a relation of type `function-in-act` (origin = person,
   destination = act, value = the function/role). Identity assertions are
   relations of type `identification`.
4. **Provenance is everywhere.** Each entity records the `source` id it
   came from, its position in the source (`the_line`, `the_level`,
   `the_order`), its containing group (`inside`), and the Kleio group
   name that produced it (`groupname`). Two databases of the same sources
   have the same ids; different sources generate different ids.
5. **Classes are dynamic.** The set of entity classes is itself stored in
   the database (`classes` + `class_attributes` tables). A project can
   define new Kleio groups that map to new specialization tables created
   at import time. Never assume the class list; enumerate it.

## 2. Core tables

### `entities` — one row per entity (the spine)

| Column | Meaning |
|---|---|
| `id` | unique entity id (string; often the Kleio group id, e.g. `140338`) |
| `class` | entity class: `person`, `act`, `source`, `object`, `geoentity`, `attribute`, `relation`, `rentity`, `aregister`, or a dynamic class |
| `inside` | id of the entity containing this one (nesting in the source) |
| `the_source` | id of the `source` entity this entity was extracted from |
| `the_order`, `the_level`, `the_line` | position in the source: sequence, nesting depth, line number |
| `groupname` | Kleio group that produced the entity (e.g. `n` for a person group in the tutorial data) — data dependent |
| `extra_info` | JSON with import-time details: original wording, comments, kleio element names per column |
| `updated`, `indexed` | maintenance timestamps |

### `persons` — specialization of entity (`class = 'person'`)

| Column | Meaning |
|---|---|
| `id` | same as `entities.id` |
| `name` | the name as written in the source (may vary across sources) |
| `sex` | `m` / `f` / empty |
| `obs` | free-text observation |

### `attributes` — properties of an entity

| Column | Meaning |
|---|---|
| `id` | id of the attribute-as-entity |
| `entity` | **id of the entity described** (the join key) |
| `the_type` | attribute type, e.g. `naturalidade`, `grau`, `faculdade`, `jesuita-entrada` — vocabulary is data-dependent |
| `the_value` | attribute value |
| `the_date` | date as string (see §4) |
| `obs` | free text |

Indexed on (`the_type`, `the_value`) — type+value searches are the fast
path. One entity can have many attributes of the same type (values over
time, or from different sources).

### `relations` — connections between entities

| Column | Meaning |
|---|---|
| `id` | id of the relation-as-entity |
| `origin` | id of the subject entity |
| `destination` | id of the object entity |
| `the_type` | relation type, e.g. `function-in-act`, `identification`, `kinship`, ... — data-dependent |
| `the_value` | e.g. the role/function for `function-in-act` |
| `the_date` | date as string |
| `obs` | free text |

Direction matters: `origin` → `destination`. For persons in acts:
`origin` = person, `destination` = act. For `identification`: `origin` =
occurrence, `destination` = the "real" identity.

### `acts` — historical events (`class = 'act'`)

`id`, `the_type` (act type), `the_date`, `loc` (place), `obs`. Participants
are not columns: they are `relations` rows with `destination` = act id and
`the_type = 'function-in-act'` (`the_value` = role such as `pai`, `mãe`,
`noivo`, `testamenta`...).

### `sources` — provenance documents (`class = 'source'`)

`id`, `the_type`, `the_date`, `loc`, `ref` (archive reference),
`kleiofile` (the Kleio source file), `replaces`, `obs`. Sources nest
(`inside`): a book contains registers contains entries.

### `objects`, `geoentities` — other named things

`objects`: `id`, `name`, `the_type`, `obs`. `geoentities`: `id`, `name`,
`the_type`, `obs`. Both can carry attributes and relations like persons.

### `rentities` + `links` — real entities / deduplication (advanced)

`rentities`: `id`, `user` (who asserted it), `description`, `status`
(`valid`/`invalid`/`possible`), `obs` — a "real person" that multiple
source occurrences refer to. `links` connect a `rentity` to the source
occurrences (entities) it identifies, with `rule`, `status`, `date`.
Ignore these unless the task is identity resolution.

### `classes`, `class_attributes` — the meta-model

`classes`: `id` (class id used in `entities.class`), `table_name`,
`group_name` (default Kleio group for the class), `super`.
`class_attributes`: how Kleio group elements map to columns.
This is where dynamic classes are declared — enumerate with
`db_schema` (no target) instead of assuming the list above.

### `kleiofiles` — import bookkeeping

`path` (pk), `name`, `structure`, `translator`, `translation_date`,
`nerrors`, `nwarnings`, `error_rpt`, `warning_rpt`, `imported`,
`imported_string`. Powers `get_import_status` and the report tools.
(`syspar` holds system parameters; rarely relevant.)

## 3. Views (pre-joined shortcuts)

| View | Joins | Use for |
|---|---|---|
| `named_entities` | entities ∪ persons/objects/geoentities names | list of named things with `name`, `groupname`, `pom_class`, provenance |
| `nattributes` | named_entities + attributes | attributes with entity name/group |
| `eattributes` | entities + attributes, incl. attribute's own provenance (`a_the_line`, `a_the_level`, `a_groupname`, `a_extra_info`) | the workhorse behind `find_entities_by_attribute` |
| `nrelations` | relations + named_entities on both sides | relation search with both parties' ids and names: `relation_id, origin_id, origin_name, destination_id, destination_name, relation_type, relation_value, relation_date` |
| `nfunctions` | function-in-act relations + named entities | who did what in which act |

## 4. Conventions that are easy to get wrong

* **Dates are strings, not date types.** Format `yyyymmdd` with partial
  dates allowed (`1712`, `171203`, `17120300` when day unknown). Filter by
  lexical range: `dates_in = ["1535", "1600"]` matches years 1536–1599
  (bounds are exclusive). Never cast to SQL date types; compare as
  strings.
* **`the_type`/`the_value` vocabularies are data-dependent.** Always list
  the vocabulary first (`attribute_values` tool) before filtering on
  values; `naturalidade` in one project is `local-nascimento` in another.
  Values can also be checked with wildcards: `the_value = "Coimbra%"`.
* **`class` vs `groupname` vs table name.** `entities.class` selects the
  specialization table; `groupname` is the Kleio group (many groups can
  map to one class — several person-like groups → `person`). Use
  `class`/`entity_type` for queries; use `groupname` when you want to
  restrict to one source structure.
* **Ids are strings** even when they look numeric (`'140338'`). Quote them.
* **Duplicate persons are expected.** The same historical person appears
  once per source with different ids; attributes from different sources
  attach to different occurrence-ids. Consolidation is via
  `rentities`/`links` or `identification` relations — do not assume
  name equality.
* **`extra_info` JSON** may carry the original wording and comments of a
  value (`...original`, `...comment` columns in pandas results). When
  precision matters, look there.
* **Acts have no participant columns** — always go through relations.

## 5. Recipes (task → tool)

| Question | Tool / view |
|---|---|
| What values does attribute `naturalidade` have? | `attribute_values(the_type="naturalidade")` (`nattributes`) |
| People born in Soure with extra columns? | `find_entities_by_attribute(the_type="naturalidade", the_value="Soure", more_attributes=[...])` |
| Everything about person `140338`? | `entity_attributes(ids=["140338"])`, then `entity_details` for the Kleio rendering with inline relations |
| Who is this person related to? | `entity_relations(id="140338")` (`nrelations` filtered by `origin_id`/`destination_id`) |
| All kinship relations? | `find_relations(relation_type="kinship%")` (`nrelations`) |
| Participants of act `a1688-12-05-3-f?` | `entity_relations(id=<act-id>)` or `nfunctions` |
| Where does an entity come from? | `entities.the_source` → `sources` row → `kleiofile`; line/level in the entities row |
| What classes/groups exist here? | `db_schema` (lists `Entity.group_models` and `classes`) |

## 6. Delivery plan

1. Ship this document, per database, as an MCP **resource**
   (`timelink://schema/<database>`) — `db_schema` links to it; the
   class/group list in the resource is generated at connect time from
   `classes`/`class_attributes` (static base part + dynamic part).
2. Include the conceptual model (§1) and conventions (§4) essentially
   verbatim in the project `AGENTS.md`, since they apply to every
   database; per-database specifics (vocabularies, class list) stay
   dynamic in the resource.
