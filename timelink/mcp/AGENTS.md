# Timelink MCP server — guide for agents

How to use the Timelink MCP tools. The conceptual model and conventions
below apply to **every** Timelink database; per-database specifics
(vocabularies, class lists, table catalogue, query recipes) are in the
`timelink://schema/{database}` resource — read it before heavy querying.

The tool set is specified in `docs/mcp-tools-draft.md` (18 tools, four
groups). Tabular tools take `row_limit`/`offset` and return
`{rows, row_count, truncated, next_offset}` — page with `next_offset`
instead of asking for huge pages; the server caps pages at
`TIMELINK_MCP_MAX_ROWS` (default 500).

## When to reach for each tool

| You want to… | Tool |
|---|---|
| See which projects exist (including ones with no database yet) | `list_projects` |
| See which databases exist | `list_databases` → `db_info` → `db_schema` |
| Know what an attribute type can be | `attribute_values` — **always before** filtering on values |
| Find entities by a property | `find_entities_by_attribute` (the workhorse) |
| Find a person by name | `find_persons_by_name` (`similar=true` strips de/da/dos/…) |
| The full profile of one entity | `entity_attributes` (table) or `entity_details` (Kleio rendering, ≤5 ids) |
| Relations of one entity | `entity_relations`; population-level relation search → `find_relations` |
| Update the database from sources | `get_import_status` → `translate_sources` → `wait_for_translations` → `import_from_sources` → `get_import_status` |
| Understand a failed translation/import | `get_translation_report` / `get_import_report`; `kleio_server_info` if the server itself is the problem |

The **attribute-values-before-search pattern**: vocabularies are
data-dependent (`naturalidade` in one project is `local-nascimento` in
another). Call `attribute_values(the_type=...)` first, then filter —
wrong-value searches silently return nothing, they don't error.

**Database names in multi-project homes.** `list_databases` searches the
whole timelink home recursively, so the same database name can exist in
several projects (each listing entry carries its `project` and `path`).
A bare name that matches several databases raises an error listing the
candidates — disambiguate with the qualified `project/name` form or a
path.

## Conceptual model

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
   at import time. Never assume the class list; enumerate it with
   `db_schema`.

## Conventions that are easy to get wrong

* **Dates are strings, not date types.** Format `yyyymmdd` with partial
  dates allowed (`1712`, `171203`, `17120300` when day unknown). Filter by
  lexical range: `dates_in = ["1535", "1600"]` matches years 1536–1599
  (bounds are exclusive). Never cast to SQL date types; compare as
  strings.
* **`the_type`/`the_value` vocabularies are data-dependent.** Always list
  the vocabulary first (`attribute_values` tool) before filtering on
  values. Values can also be checked with wildcards: `the_value = "Coimbra%"`.
* **String filters are SQL LIKE** (`%` any string, `_` one char); lists
  mean exact IN-match. `find_entities_by_attribute` applies LIKE when
  `the_type`/`the_value` is a string and IN when it is a list.
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
  value. When precision matters, look there.
* **Acts have no participant columns** — always go through relations.

## The update workflow

The pipeline is split so you stay in control; each step returns promptly.
With no `path` argument the tools operate on the **database's own project
sources** (`projects/<project>/sources` in a multi-project home) — pass an
explicit path only to reach beyond it.

1. `get_import_status` — what is stale? Translation statuses:
   `T` needs translation, `P/Q` in progress/queued, `V` valid,
   `W` warnings, `E` errors. Import statuses: `N` new, `U` needs reimport,
   `I` imported, `W`/`E` imported with warnings/errors.
2. `translate_sources` — request translations of the stale files
   (`force=true` for everything). Returns immediately with the list.
3. `wait_for_translations` — bounded wait (default 120 s). Re-invoke while
   `still_pending` is non-empty. Failed translations are retried once
   automatically; a second failure lands in `failed`.
4. `import_from_sources` — import what is ready and new/updated. Returns
   per-file stats plus `skipped` files with reasons.
5. `get_import_status` again — compare before/after.
6. For any file with errors or warnings: `get_translation_report(file)`
   (Kleio server side) and `get_import_report(file)` (database side).
   `kleio_server_info` shows the server's url/version/health if updates
   misbehave (the token is never exposed).

Deliberately absent from v1: raw SQL `query` (use the curated tools),
write operations other than the import pipeline, and network generation.
