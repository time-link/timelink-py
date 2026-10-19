# Timelink MCP server — proposed tool call set (draft)

Status: **validated** (open questions resolved 2026-10-03, see §6). Every
tool below is mapped to the exact
`timelink-py` library call it would wrap, so it can be checked against the
package code and the tutorial notebooks
(`tests/timelink-home/projects/tutorial/notebooks/02-tutorial.ipynb`).

Target users: AI agents that need to (1) discover Timelink databases,
(2) search them by attributes and relations, (3) explore the relations of
specific entities, and (4) update databases from Kleio source files.

---

## 1. Server model

The MCP server is a long-running Python process holding state that agents
should not have to manage:

* **Database connections.** A cache of `TimelinkDatabase` instances keyed by
  `(db_type, db_name)`. Tools take a `database` name parameter; the server
  resolves it (from the list returned by `list_databases`) and connects on
  first use. Connections are reused across calls.
* **Kleio server.** One Kleio server per server process, started lazily
  (only by the source-update tools): `KleioServer.start(kleio_home=...)` or
  `KleioServer.attach(url, token)` when a server is already running.
  Query-only calls never touch Docker.
* **Credentials.** Postgres password and Kleio token come from environment
  variables / keychain helpers; they are **never** included in tool output
  (mirrors `TimelinkNotebook.print_info(show_token=False)`).

### Environment configuration

Five variables; `TIMELINK_MCP_HOME` alone covers a standard deployment.

| Variable | Purpose | Default |
|---|---|---|
| `TIMELINK_MCP_HOME` | the timelink/kleio home: root searched recursively for `*.sqlite` databases **and** home of a locally started Kleio server | `~/.timelink` |
| `TIMELINK_MCP_SQLITE_ROOT` | override the database search root — only when databases live outside the home, or to narrow scope to one directory | `TIMELINK_MCP_HOME` |
| `TIMELINK_MCP_DB_TYPE` | `sqlite` or `postgres` | `sqlite` |
| `TIMELINK_MCP_KLEIO_URL` + `TIMELINK_MCP_KLEIO_TOKEN` | attach to a running Kleio server instead of starting one | none |
| `TIMELINK_MCP_MAX_ROWS` | hard cap on rows returned per page by any tool | `500` |

One home root covers every documented timelink-home layout: single
project (`<home>/database/sqlite`), multi-project
(`projects/<project>/database/sqlite` plus `system`), project with
git-submodule subprojects and legacy MHK (`sources/<project>/database`)
— the root is walked recursively, so all projects' databases are
discovered from it.

## 2. Conventions shared by all tools

* `database` (string, required except on `list_databases`): database name as
  shown by `list_databases`. In a multi-project home the same name can
  exist in several projects; then use the qualified `project/name` form
  (or a path, absolute or relative to the search root). A bare name that
  matches several databases raises an error listing the candidates.
* **Row limits and paging.** Every tabular tool takes `row_limit`
  (default 30) and `offset` (default 0), and returns
  `{rows: [...], row_count, truncated, next_offset}` — `next_offset` is
  present when more rows exist, so the agent can either page through a
  large result or refine the search. The server enforces
  `TIMELINK_MCP_MAX_ROWS` (500 by default) as the per-page hard cap; the
  cap is a deployment setting, raised via the environment variable when a
  use case needs bigger pages.
* **Dates** are Timelink date strings compared lexically: `yyyy`,
  `yyyymm` or `yyyymmdd` (e.g. `dates_in=["1535","1600"]`, as used in the
  tutorial notebook for `attribute_values`).
* **Wildcards.** String filters passed to the library use SQL `LIKE`
  semantics (`%` any string, `_` one char). Lists mean exact IN-match.
  `entities_with_attribute` applies `LIKE` when `the_type`/`the_value` is a
  string and `IN` when it is a list — the tool exposes both via
  `string | string[]`.
* **Entity ids** are the alphanumeric ids used in the database (e.g.
  `140338` in the tutorial) and in Kleio files.
* Returns are JSON objects (DataFrames serialized as records); `null`
  results from the library become empty `rows: []`.

## 3. Proposed tools

Names are unprefixed (the MCP server name `timelink` already namespaces
them in clients). 18 tools in four groups.

### A. Discovery

#### 3.1 `list_projects`

List the Timelink projects under the configured home. Projects are
detected structurally — a directory with a `.timelink-project` marker,
or a `database/`, `structures/` or `sources/` child — not from
database files, so projects whose sources were never imported are
listed too (`has_database` and `databases` show the gap). Orientation
entry point: this first, then `list_databases` for the databases.

| Param | Type | Default | Notes |
|---|---|---|---|
| `directory` | string | env search root | override the root for this listing |

Library calls: `timelink.api.projects.get_timelink_projects(root)`
(package-level structural discovery, shared with the webapp and the
CLI; the MCP tool delegates to it).

Returns: `{root, projects: [{name, path, relative_path, marker,
has_database, has_structures, has_sources, inside, databases: [{name,
path}]}], project_count, databases_without_project}`. `inside` is the
enclosing project's relative path, set for git-submodule subprojects
nested in a parent project's sources; `is_home` marks the
single-project-home root (the root itself has the layout); home
infrastructure such as the multi-project `system` directory is not a
project, and sqlite files under it are counted in
`databases_without_project`.

#### 3.2 `list_databases`

List the Timelink databases available on this machine. The configured
root (the timelink home, by default) is searched recursively, so every
project of a multi-project home is listed, each database annotated with
its project — the nearest ancestor directory discovered as a project
by the structural rules of `list_projects` (§3.1).

| Param | Type | Default | Notes |
|---|---|---|---|
| `db_type` | `sqlite\|postgres\|all` | from env | restrict to one engine |
| `directory` | string | env search root | sqlite only — override the root for this listing |

Library calls: `get_sqlite_databases(root)` → `list[str]` (recursive
walk, same discovery the CLI's `timelink db list` does from the working
directory); `get_postgres_dbnames()` (needs the `timelink-postgres`
Docker container running).

Returns: `{default_db_type, sqlite_root, databases: [{name, project,
db_type, path}]}` (path only for sqlite); `project` is null for
databases outside any project. Only `*.sqlite` files are listed and
connectable — the extension `TimelinkDatabase` opens.

#### 3.3 `db_info`

Connect to a database and report its contents: row counts per table,
available entity classes, views, database (alembic) version. This is the
"what is in this database" entry point, equivalent to the
`tlnb.print_info()` / `tlnb.table_row_count_df()` cells in the tutorial.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |

Library calls: `TimelinkDatabase(db_name, db_type)` (cached);
`db.table_row_count()`; `db.get_models_ids()`; `db.view_names()`;
`db.get_database_version()`.

Returns: `{tables: [{name, rows}], entity_classes: [...], views: [...],
version, kleio_server_attached: bool}`.

#### 3.4 `db_schema`

Describe one entity class / table / view (columns, types, foreign keys), or
list the Kleio-group → ORM-class mapping when called without a target —
this tells the agent which `entity_type` values and which attribute-bearing
groups exist. Mirrors the `A2-database-explore.ipynb` cells
(`get_models_ids()`, `describe(model, show=True)`).

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `model_or_table` | string | none → list group/model mapping |

Library calls: `db.describe(argument)`; `db.get_columns(name)`;
`Entity.group_models` for the group mapping.

Companion to this tool, the server exposes the static schema reference
(`docs/mcp-db-structure-draft.md`, to become the MCP resource
`timelink://schema/<database>`) with the conceptual model, table/view
catalogue, date/id/wildcard conventions and query recipes. Tools reference
it in their descriptions so agents know where to look before querying.

### B. Search by attribute

#### 3.5 `attribute_values`

Vocabulary of one attribute type: distinct values with the number of
distinct entities and first/last dates. The agent's tool for "what are the
possible values of `naturalidade` / `grau` / `jesuita-entrada`?" before
searching.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `the_type` | string | required |
| `groupname` | string \| string[] | none (all groups) |
| `dates_between` | [from, to] | none |
| `row_limit` | int | 50 |

Library call: `timelink.pandas.attribute_values(...)` → DataFrame indexed
by `value` with `count`, `date_min`, `date_max`.

#### 3.6 `find_entities_by_attribute` *(workhorse)*

Entities having a given attribute, with value/date/name filters, optionally
enriched with further attributes. This is the tutorial's main search cell.

| Param | Type | Default | Notes |
|---|---|---|---|
| `database` | string | required | |
| `the_type` | string \| string[] | required | e.g. `"naturalidade"`, `"jesuita-entrada"` |
| `the_value` | string \| string[] | none | e.g. `"Soure"` or `"Coimbra%"` |
| `entity_type` | string | `"person"` | one of `db_schema` values (`person`, `object`, `act`, `entity`, dynamic classes) |
| `show_elements` | string[] | `["name"]` | entity columns to include |
| `more_attributes` | string[] | none | extra attribute types joined as columns |
| `dates_in` | [after, before] | none | exclusive bounds |
| `name_like` | string | none | LIKE filter on entity name |
| `row_limit` | int | 30 | |

Library call: `timelink.pandas.entities_with_attribute(...)`.

Returns rows keyed by entity id with `name`, the attribute value, date,
obs, line/level (provenance in the source), plus one column per
`more_attributes`.

#### 3.7 `find_persons_by_name`

Persons whose name matches a pattern (or a fuzzy match with particles
removed).

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `name` | string | required, `%` wildcards allowed |
| `similar` | bool | `false` (library strips `de/da/dos/...` and inserts `%` between components) |
| `row_limit` | int | 30 |

Library call: `timelink.pandas.pname_to_df(name, similar=...)` →
`id, name, sex, obs`.

#### 3.8 `entity_attributes`

All attributes of one or more entities (the "person profile" table), with
optional include/exclude attribute filters. Tutorial cell: `id = '140338';
group_attributes([id], db=...)` sorted by date.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `ids` | string[] | required |
| `entity_type` | string | `"person"` |
| `include_attributes` | string[] | none |
| `exclude_attributes` | string[] | none |
| `show_elements` | string[] | `["name"]` |
| `row_limit` | int | 100 |

Library call: `timelink.pandas.group_attributes(group=ids, ...)` → rows
`the_type, the_value, the_date, attr_obs` per id.

#### 3.9 `entity_details`

Full rendering of an entity (and, optionally, its containing source/act
hierarchy) in Kleio notation — the richest view of one entity, including
inline relations and observations. Tutorial cell:
`p = tlnb.db.get_person(id); print(p.to_kleio())`.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `ids` | string[] | required (≤ 5 per call) |
| `format` | `kleio\|markdown` | `kleio` |

Library calls: `db.get_entity(id)` / `db.get_person(id)`;
`entity.to_kleio()`; `entity.to_markdown()` where available
(`Relation.to_markdown` exists).

### C. Relations

#### 3.10 `find_relations`

Search the relation space by type, value, date and/or the parties involved.
Built on the `nrelations` view (relations joined with `named_entities` on
both sides), which yields both parties' ids and names.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `relation_type` | string | none, LIKE allowed (e.g. `kinship%`, `function-in-act`) |
| `relation_value` | string | none |
| `origin_id` / `destination_id` | string | none |
| `origin_name` / `destination_name` | string | none, LIKE allowed |
| `dates_in` | [after, before] | none |
| `row_limit` | int | 30 |

Library calls: `db.get_view("nrelations")` + `db.select(...,
as_dataframe=True)` with the filters. View columns: `relation_id,
origin_id, origin_name, destination_id, destination_name, relation_type,
relation_value, relation_date`.

#### 3.11 `entity_relations`

All relations of one entity, outgoing and/or incoming, with the name and
class of the other side. This is the "explore the relations of X" tool; the
agent chains it to drill into specific counterparts.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `id` | string | required |
| `direction` | `out\|in\|both` | `both` |
| `relation_type` | string | none |
| `row_limit` | int | 50 |

Library calls: `Entity.get_entity(id, session)` → `rels_out` / `rels_in`
(or the same `nrelations` query filtered by `origin_id`/`destination_id`).
Each row: `direction, relation_type, relation_value, relation_date, obs,
other_id, other_name, other_class`.

### D. Sources and updating

#### 3.12 `translate_sources`

Request translations on the Kleio server for the sources that are stale
(source newer than translation), without waiting. First step of the update
pipeline; the agent follows it with `wait_for_translations` (or polls
`get_import_status`) and then `import_from_sources`.

| Param | Type | Default | Notes |
|---|---|---|---|
| `database` | string | required | |
| `path` | string | project sources | Kleio-server-relative path; default scopes to the database's project (`projects/<p>/sources` in a multi-project home, `sources` in a single-project one) |
| `recurse` | bool | `true` | |
| `force` | bool | `false` | request translation of every file, not only stale ones |

Library calls (the first block of `db.update_from_sources`,
`database_kleio.py`): `kserver.get_translations(path, recurse,
status="T")` (all files when `force`), then
`kserver.translate(kfile.path, recurse="no", spawn="no")` per file. The
wrapper remembers the requested paths (the server process is stateful) for
`wait_for_translations`.

Returns: `{requested: [{path, status}], count, kleio_server}` — the
status each file had when the translation was requested (`T` normally,
anything with `force`).

#### 3.13 `wait_for_translations`

Block until the translations requested by the last `translate_sources`
call reach a terminal status (`V` valid, `W` warnings, `E` errors), then
report. Bounded by `max_wait`, so the tool call stays short — the agent
re-invokes while files are still pending, and can interleave other calls.
Gives the agent visibility into a pipeline the library otherwise hides
inside one blocking call.

| Param | Type | Default | Notes |
|---|---|---|---|
| `database` | string | required | |
| `files` | string[] | none → paths from last `translate_sources` | explicit override |
| `max_wait` | int | `120` | seconds; return with `still_pending` after this |

Library calls: polling loop over `kserver.get_translations(path,
recurse)` with the retry semantics of `db._wait_for_translations`
(`database_kleio.py`): a file that reverts from queued/processing (`Q`/`P`)
back to `T` failed and is re-requested **once**; a second failure ends
with an error. The wrapper re-implements the loop on the public
`get_translations` so it can return per-file outcomes (the library method
only logs them). Progress notifications may be emitted while polling.

Returns: `{finished: [{path, status}], failed: [{path, reason}],
still_pending: [path], waited_seconds}`.

#### 3.14 `import_from_sources`

Import into the database the files whose translations are ready and that
are new or updated since the last import. Final step of the update
pipeline.

| Param | Type | Default | Notes |
|---|---|---|---|
| `database` | string | required | |
| `path` | string | project sources | default: the database's project sources |
| `recurse` | bool | `true` | |
| `force` | bool | `false` | import every translated file, ignoring import status |
| `with_import_errors` | bool | `false` | retry files that previously failed to import |
| `with_import_warnings` | bool | `false` | retry files imported with warnings |
| `with_translation_errors` | bool | `false` | import translations that finished with errors |
| `with_translation_warnings` | bool | `true` | import translations that finished with warnings |
| `match_path` | bool | `false` | match database records by full path, not filename |

Library calls (the import block of `db.update_from_sources`):
`kserver.get_translations(path, recurse, status="V")` plus `W`/`E` per the
flags; `db.get_need_import(files, with_import_errors,
with_import_warnings, match_path)` (skipped when `force`);
`timelink.kleio.importer.import_from_xml(kfile.xml_url, session,
options={return_stats, kleio_token, kleio_url, mode: "TL"})` per file.

Returns: `{imported: [{path, stats}], skipped: [{path, reason}]}` — the
per-file import stats the library only logs.

#### 3.15 `get_import_status`

Import/translation status of the Kleio files relative to this database —
the agent's "what would the update pipeline do / what happened" view.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `path` | string | `""` |
| `recurse` | bool | `true` |
| `status` | `N\|U\|I\|W\|E` | none |

Library calls: `db.get_import_status(path, recurse, status)`; underlying
`kserver.get_translations(...)`. Returns per file: translation status
(`V/W/E/T/P/Q`), errors, warnings, import status (`N/U/I/W/E`).

#### 3.16 `get_import_report`

The import error/warning report stored in the database for one file.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `file` | string | required (name or full path) |
| `match_path` | bool | `false` |

Library call: `db.get_import_rpt(path, match_path)` → text.

#### 3.17 `get_translation_report`

The Kleio-server translation report for one file.

| Param | Type | Default |
|---|---|---|
| `database` | string | required |
| `file` | string | required (Kleio server path) |

Library call: `db.get_kleio_server().get_report(rpt_url)` → text
(pattern from `TimelinkNotebook.get_translation_report`).

#### 3.18 `kleio_server_info`

URL, Kleio version, home directory and health of the attached Kleio server
(no token). For diagnosing failed updates. Library calls:
`kserver.get_version_info()`, `kserver.get_url()`, `kserver.get_kleio_home()`.

## 4. Example agent workflows

These mirror the tutorial notebook and should work end-to-end with the set
above:

1. **"What databases do we have, what is in them?"**
   `list_databases` → `db_info` → `db_schema` (per interesting class).
2. **"Find people born in Soure that entered the university before 1550."**
   `attribute_values(the_type="naturalidade")` (check vocabulary) →
   `find_entities_by_attribute(the_type="naturalidade", the_value="Soure",
   more_attributes=["uc.entrada","faculdade"])` →
   `entity_attributes(ids=[...])` or `entity_details` for the interesting
   ones.
3. **"Who is related to João de Andrade (id 140338) and how?"**
   `find_persons_by_name(name="%Andrade%")` →
   `entity_relations(id="140338")` → `entity_details` on counterpart ids;
   or `find_relations(relation_type="kinship%")` for the population-level
   question.
4. **"Update the database from the transcription files and tell me what
   happened."**
   `get_import_status` (what is stale) → `translate_sources` →
   `wait_for_translations` (re-invoke while `still_pending` non-empty, or
   poll `get_import_status`) → `import_from_sources` →
   `get_import_status` (after); `get_translation_report` /
   `get_import_report` on any file with errors or warnings.

## 5. Deliberately out of scope (first cut)

* `network_from_attribute` (networkx graphs — visualization-oriented; an
  agent gets the same information from `attribute_values` +
  `find_entities_by_attribute`).
* `query` (raw read-only `SELECT` via `db.select`) — held back from v1
  per the validation decision below; add it if the curated tools prove
  insufficient for real agent questions.
* Write operations other than the import pipeline (creating entities,
  acts, deduplication/`same_as` merges).
* Kleio server lifecycle management (start/stop containers) — the server
  attaches/starts silently; `kleio_server_info` reports state.
* MHK legacy mode (`import_from_xml` with `mode="MHK"`).

## 6. Validation decisions (2026-10-03)

The open questions were answered; the tool set above already reflects the
decisions.

1. **`entity_type` default: keep `person`.** It matches the dominant
   prosopography use case; other types stay one parameter away.
2. **Row limits: default 30, cap 500 — with paging.** The cap stays a
   deployment setting (`TIMELINK_MCP_MAX_ROWS`), and tabular tools gained
   `offset` / `next_offset` paging (§2) so large results are walked in
   pages instead of needing a bigger cap.
3. **`query` escape hatch: hold SQL back.** Raw SELECT is out of v1
   (§5); it is added later only if the curated tools prove insufficient.
4. **Update pipeline: split, so the agent orchestrates.** The single
   blocking `update_from_sources` call is replaced by
   `translate_sources` → `wait_for_translations` → `import_from_sources`
   (§3.12–3.14), each bounded and inspectable, with `get_import_status`
   as the polling view. The one-shot library method remains available to
   the wrapper internally but is not exposed as a tool.
5. **Default `db_type`: sqlite.** Confirms the env default in §1; Postgres
   remains a `db_type` parameter / env switch away.
6. **Naming: no preference expressed.** Keep the draft's unprefixed names;
   revisit only if a client shows tools without the server namespace and
   collisions appear.
7. **Multi-project homes (revised 2026-10-03, after initial
   implementation).** The original `TIMELINK_MCP_SQLITE_DIR` assumed one
   flat sqlite directory — true only of the single-project layout.
   Replaced by the scheme in §1: `TIMELINK_MCP_HOME` (one root for
   databases and the Kleio server) plus optional
   `TIMELINK_MCP_SQLITE_ROOT` override; the root is walked recursively
   (all four documented home layouts), listings are project-annotated,
   and `database` parameters take `project/name` or a path when a bare
   name is ambiguous. `TIMELINK_MCP_KLEIO_HOME` is gone — a locally
   started Kleio server uses the home; a remote one is attached via
   URL/TOKEN. The source-update tools (§3.12–3.15) follow the same
   principle: their `path` defaults to the database's own project
   sources rather than the whole Kleio server — a whole-server default
   in a multi-project home requests translations for other projects'
   files and trips the library's duplicate-filename check.
8. **Project discovery is structural, not database-driven (added
   2026-10-03, after initial implementation).** `list_databases` cannot
   answer "what projects exist": a project whose sources were never
   imported has no sqlite file to find, so it was invisible. The new
   `list_projects` (§3.1) detects projects by layout — a
   `.timelink-project` marker, or a `database/`, `structures/` or
   `sources/` child directory — and walks into `sources/` so
   git-submodule subprojects are reported as nested. `list_databases`
   project annotations now use the same discovery (nearest project
   ancestor), so the two tools agree; the root itself counts as a
   project only under the strict rule (marker/`database`/`structures`)
   because a bare `sources/` child at the root is the legacy-MHK
   container of projects, not a project; the multi-project `system`
   directory is home infrastructure, never a project. The discovery
   lives in the package (`timelink/api/projects.py`, also exported from
   `timelink.api.database` as `get_timelink_projects`) — following the
   `timelink_home` reference doc, both markers are honored
   (`.timelink-project` marks a project, `.timelink-home` marks a
   multi-project home container) — and `TimelinkWebApp`'s project
   listing was refactored onto it, so the webapp registry gains the
   legacy and marker-based layouts instead of trusting every directory
   under `projects/`. The MCP layer delegates and adds the database
   attachment (`list_projects` output).

## 7. Implementation status (2026-10-03)

Implemented as the `timelink.mcp` subpackage (nested like `timelink.app`
rather than a top-level `mcp_server/`, so it ships with the timelink
wheel and does not pollute the top-level namespace):

1. **Server** (`timelink/mcp/`): `server.py` (FastMCP assembly, works
   with both mcp 1.x and 2.x), `config.py` (env settings), `databases.py`
   (connection cache; never creates databases; project annotations and
   `list_projects` delegate to `timelink/api/projects.py`, the
   package-level structural discovery of §3.1), `kleio.py` (lazy
   Kleio-server start/attach + translation bookkeeping), `paging.py`
   (row limits/paging), `tools/` (one module per group, plain testable
   functions + `register(mcp)`). Entry points: `timelink-mcp` console
   script and `python -m timelink.mcp` (stdio). Dependency: extra
   `timelink[mcp]`.
2. **AGENTS.md**: `timelink/mcp/AGENTS.md` — tool-selection table,
   attribute-values-before-search pattern, conceptual model and
   conventions (from `docs/mcp-db-structure-draft.md` §1/§4), update
   workflow. The structure reference ships as the packaged resource
   `timelink/mcp/data/db-structure.md`, served at
   `timelink://schema/{database}`.
3. **Tests**: `tests/test_140_mcp_server.py` — builds the reference
   database through the session Kleio-server fixture (as `test_040`),
   configures the MCP context to attach to it, and exercises all 18
   tools including the split update pipeline; plus Docker-free tests for
   settings, resource content, tool registration and the project
   layouts of `list_projects`.
