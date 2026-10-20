# MHK (Java) web application — feature inventory

Reference inventory of the legacy Java implementation at
`/Users/jrc/develop/mhk/idb`, produced 2026-10-16 as the migration
source-of-truth. App root `idb/`, Java package `pt/uc/cisuc/jrc/mhk/`,
Velocity templates in `etc/template/{new,alt,old,xtras}/`, static
assets in `web/`, DB bootstrap SQL in `etc/db/`.

## Architecture in one paragraph

There is no per-feature servlet mapping. `web.xml` (`idb/etc/web.xml`)
registers ONE servlet — `CentralServlet` at `/servlet/do` — plus a
`CharsetFilter` (UTF-8), Tuckey `UrlRewriteFilter` (`etc/urlrewrite.xml`),
a jcaptcha servlet, two JDBC resource-refs (`jdbc/global`,
`jdbc/mhk_users`) and a `SessionManagerUser` listener. Every request is
`/servlet/do?action=<name>&dbname=<db>&...`; `CentralServlet.processRequest()`
is a big if-chain mapping `action` → `Command` object which returns a
Velocity template name. **The Velocity templates themselves execute SQL
through `$db` (`DBSystem`) — a lot of business logic lives in `.vm`
files, not Java.** Two JNDI datasources: one for the research DBs (one
MySQL schema per project, per-user whitelist `mhk.dbnames.USER`), one
for the `mhk_users` user/comment DB.

## A. Route map

### URL rewrite rules (`etc/urlrewrite.xml`)

| Pretty URL | Rewritten to |
|---|---|
| `/login/` | `?action=login.vm` |
| `/signup/` | `?action=signup.vm` |
| `/terms_conditions/` | `?action=terms_conditions.vm` |
| `/{dbname}/home/` | `?dbname=$1&action=exec&script=search.vm` |
| `/{dbname}/id/{id}` | `?dbname=$1&action=show&id=$2` (entity permalink) |
| `/{dbname}/exec/{script}` | `?dbname=$1&action=exec&script=$2` |
| `/{dbname}/show/{action}` | `?dbname=$1&action=$2` |
| `/{dbname}/query/{sql}` | `?dbname=$1&action=query&sql=$2` |

### Action dispatch (`CentralServlet.processRequest`; level = user level 1/2/3)

| `action=` | Servlet class | Level | Purpose |
|---|---|---|---|
| `search` | (→ `search.vm`) | any | Home/search page |
| `show` | `ShowEntity` | any | Display entity by `id`; auto-detects real vs occurrence entity → `entity_show.vm` router |
| `query` | `ShowQuery` | any | Run SQL (`sql` param or shortcuts `attribute_type`, `attribute_value`, `rel_name_out`, `rel_name_in`, `name`) |
| `exec` | `DoExec` | any | **Execute any template by name** (`script` param) — generic page runner / fallback |
| `execFamily` | `DoExecFamily` | any | Template execution + GEDCOM family pre-computation side effect |
| `dologin`/`login`/`logout` | `DoLogin`/`login.vm`/`Logout` | – | Session login/logout |
| `show_sources` | `ShowSources` | any | Sources browser + translation/import status + git |
| `showfile` | `ShowFileFromService` | any | Fetch file content from Kleio server |
| `showrpt` | `DoShowRpt` | any | Show Kleio translation report (.rpt/.err) |
| `show_acts` | `ShowActs` | any | Acts listing |
| `show_persons` | `ShowPersons` | any | Persons page |
| `show_groups` | `ShowGroups` | any | Entity-groups page (stub) |
| `show_attributes` | `ShowAttributes` | any | Attributes page |
| `show_relations` | `ShowRelations` | any | Relations page |
| `show_xtras` | `ShowXtras` | any | Lists optional template packs |
| `show_linking` | `ShowLinkingInfo` | >1 | Linking dictionary status/import/export |
| `personlist` | `DoPersonList` | any | Person id list for manual identification |
| `sameas` | `DoSameAs` | >1 | Merge occurrences: create `/Identification/same-as` links to target real person |
| `unlink` | `DoUnlink` | >1 | Remove occurrence from real person |
| `changerpname` | `DoChangeRPName` | >1 | Change real person display name |
| `saveldict` / `loadldict` | `DoSave/LoadLinkingDictionary` | any | Export/import linking dictionary (background workers) |
| `translate` | `DoTranslate` | >2 | Ask Kleio server to translate sources (JSON-RPC) |
| `import` | `DoImport` | >2 | Import translated XML into DB (queued worker) |
| `importoutput` | `DoImportOutput` | >2 | Show import job output |
| `translator_output` | `DoTranslatorOutput` | >2 | Show translation job output |
| `prologoutput` | `DoPrologOutput` | >2 | Legacy prolog engine output |
| `processfiles` | `DoProcessFiles` | >2 | Batch translate/import selected files |
| `processGit` | `DoGitCmd` | >2 | Git commit/pull/push/revert on sources via Kleio server |
| `edit` | `DoEdit` | >2 | Open file in web editor (CodeMirror, `editor.vm`) |
| `get_file`/`save_file` | `DoGetFileContent`/`DoSaveFile` | >2 | AJAX read/write for editor |
| `upload` | `UploadFile` | >2 | Upload source file |
| `create_source` | `CreateSource` | >2 | Wizard for new Kleio source file |
| `createstorage`/`dropstorage` | `DoCreate/DoDropStorage` | >2 | Create/drop MySQL database (project storage) |
| `geoentity` | `DoGeoentity` | >2 | Add/update/delete geoentity geometry |
| `schedule` | `DoScheduleTask` | >2 | Schedule background task (`task` + `pname[]`/`pvalue[]`) |
| `show_system` | `ShowSystem` | >2 | DB stats, queued jobs, job messages, index count |
| `upgrade_settings` | `UpgradeSettings` | >2 | Migrate old `mhk.properties` |
| `saveproperties` | `SaveProperties` | >2 | Save user properties |
| `newuser`/`saveuser` | `new_user.vm`/`SaveUser` | >2 | Create user properties file |
| `insertuser` | `DoInsertUser` | >2 | Public signup (inactive row in `mhk_users.users`) |
| `validateuser` | `DoValidateUser` | >2 | Activate user via emailed code |
| `sendcomment` | `DoSendComment` | >2 | Post comment on entity (`comments` table) |

Helper classes: `Command` (base), `ConnectionManager`,
`PasswordStorage` (PBKDF2), `ResourceBundleHelper`, `URLEncoderHelper`,
`VsCodeURLMaker`, `VelocityWorker` (templates as background jobs),
`SessionManagerUser`.

## B. Functional areas

### 1. Search & browse (public level 1)
* `search.vm` (home): full-text box + entity-type radio (all/rperson/person/act) + date interval; last comments; links to advanced/expert search.
* `search_show.vm`: `MATCH(description) AGAINST(... IN BOOLEAN MODE)` on **`entitiesindex`** with class/date filters, pagination.
* `advanced_search.vm`/`advanced_search_show.vm`: (a) name search on view `nfuncs` (`name LIKE '%expr%'`, `%` between words unless quoted); (b) up to 6 attribute type/value pairs — self-joining `attributes` with `the_type LIKE`/`the_value LIKE` + date BETWEEN; attribute picklist from `select the_type from attributes group by the_type`.
* `query.vm` (level>1): raw SQL textarea → `query_show.vm` (sortable, exportable).
* `explore.vm`: entity counts by class, hotlinks into acts/persons.
* `calendar.vm`: timeline of acts per year (`left(the_date,4)` on `acts`).

### 2. Entity display
* `entity_show.vm` = **router by entity class**: person→`person_show.vm`, rperson→`rperson_show.vm`, act→`devassa_show.vm`/`default_show.vm`, caso→`caso_show.vm`, lgraph→`graph.vm`, geoentity/rgeoentity→respective; otherwise walks class hierarchy via `db.getMapping(type).super`.
* `person_show.vm`: fields, rid link + **Unlink** form, **Same-as link** form (`rperson_preview.vm` confirmation), attributes (each value hotlinks into `query&sql=attribute_value...`), in/out relations with hotlinks, "save id" cookie flag (IDList for batch same-as), comments.
* `rperson_show.vm` (real person): tabs — main data, `rperson_acts.vm`, `rperson_related.vm`, `rperson_identification.vm` (occurrences with checkboxes → batch sameas/unlink), family tab (`rperson_family*.vm` via `execFamily`, uses `rfamily`/`rchildren` or `FamilyManagement`), `rperson_preview.vm`, `changerpname` form, GEDCOM export links, comments.
* `geoentity_show.vm`/`rgeoentity_show.vm`: place entity with geometries (lat/lon), forms posting `action=geoentity`.
* `act_show.vm`, `attribute_detail.vm`, `attribute_count_show.vm`, `relation_count_show.vm`.

### 3. Record linking / identification (level ≥2) — **MHK's signature feature**
* `linking.vm`: linking dictionary status tabs (stats, export XML/JSON, import); `saveldict`/`loadldict`.
* `linking_show.vm`: all identifications by user X (`rentities where user=?` joined to `links`; highlights robot links `rule='*robot'`), batch same-as → `rentity_preview.vm`.
* `sameas_list.vm` (from `personlist`): person id list with checkboxes for manual confirmation.
* `graph.vm`: linking graph inspection for `lgraph` id — clusters from `candidates`, edges from `ledges`, `linklog`, params from `syspar where pname like 'rl.%'`.
* `lgraph_net_export.vm`: Pajek `.net` export; xtras `redes/` network exports (GDF/PAJEK via `nodes`/`edges` tables).

### 4. Sources: translate / import / git (level ≥3)
* `sources_page.vm` (+ partials): file browser over Kleio-server data; per-file status colors (needs translation / translated-needs-import / errors / warnings); buttons: translate, import, show file, show report, edit; git panel commit/push/pull/revert with user.name/email; auto-refresh 120s.
* `editor.vm`: CodeMirror editor; AJAX `get_file`/`save_file`.
* `create_source.vm`: source creation wizard.
* `translations_scheduled.vm`, `translator_output.vm`, `importer_output.vm`: job output pages.

### 5. Administration (level 3)
* `system_page.vm`: background-thread queue + messages, entity counts, indexed count, app attributes.
* `admin.vm`: edit user properties files. `new_user.vm`, signup/validation flows, `terms_conditions.vm`.
* `scheduletask.vm`: task scheduling UI.
* `xtras_page.vm`: optional template packs (queries, redes/networks, gedcom, record-linking dashboard, maintenance).

### 6. Exports
* `export.vm`: CSV of persons (one column per attribute type), rpersons links, acts.
* `ExportGEDCOM.vm`/`ExportGEDCOMall.vm`/`Pre*`: GEDCOM 5.5 via `GedComProcessing` (`$gc.gedcomFamily($rid)`), XSLT stylesheets in `etc/gedcomstylesheets/`.
* `attribute_to_kml*.vm`: KML placemarks for place attributes.
* `lgraph_net_export.vm` (Pajek), `rperson_export*.vm`, `query_export.vm`.

### 7. i18n / chrome
* `header.vm` nav bar; `$mhks` = `MHKStrings[_pt].properties` (UI), `$mhkcs` = `MHKClioStrings[_pt].properties` (Kleio terms), resolved by request locale.
* `VM_global_library.vm` macros (`#pdate`, `#coordinates`, `#showentityRelIn`...). jQuery 1.x + tablesorter + tabs + CodeMirror in `web/scripts/`.

## C. Core non-servlet Java classes (business logic to port)

### `rch/` — DB layer
* **`DBSystem.java`** (~2800 lines) — central facade: connection pooling, `createStorage`/`dropStorage`, `storeKClass/storeKGroup/storeKRelation` (import write path), `getEntityBrief/getEntityFull/getRealEntityFull`, `sqlQuery/sqlExecute...`, `getEntityCount`, `getMapping`, `getRID/getRpUsers`, search, **`processSameAs`/`unlinkSameAs`/`attach_occurence`** (identity-merge logic), `getUsersConn`, nested `DBUtils` (cursor helper exposed to templates).
* `DBEntity`, `DBREntity` (real entity + linked occurrences), `DBPerson`, `DBAttribute`, `DBRelation`, `DBClass` (class→table/column mapping), `DBGeoentity`, `DBUser` (users + comments).
* `DBSQLWorker`/`DBSQLWorkerRepeating` — queued SQL task runners.
* `IndexWorker` — search indexer (below).
* `linkingDictionary/` — `LinkingDictionary`, `LinkingDictionaryImporter`, `LinkDictImportHandler`, `XMLToLinkingDictionary`, `JSONLinkingDictionaryParser`, `RealEntityImporter`, `RealEntityToDB`, `LinkingAuthorityRegister` (aregister-based identification).

### `parser/` — Kleio/GEDCOM pipeline
* **`KleioImporterV2`** — SAX importer: XML → `XParser` → `KleioHandler` events → `DBSystem` (writes entities/attributes/relations/acts/sources/classes). *Python equivalent exists: `timelink/kleio/importer.py`.*
* `KClass/KGroup/KElement/KAttribute/KRelation/KHeader` object model. *Python equivalent: `timelink/kleio/groups/`.*
* `ImporterWorkerV2`, `TranslatorWorker`/`PrologWorker*` (legacy in-process translation), `AutoImportWorker` (repeating auto translate+import), `AutoGitWorker`, `GedcomParser`/`GedcomTranslator`/`Gedcom551ToXml` (GEDCOM→Kleio XML), `SaveWebSource`.
* `kleioserver/` — **`KleioClient`/`KleioService`** JSON-RPC client + DTOs. *Python equivalent: `timelink/kleio/kleio_server.py::KleioServer`.*

### `thread/` — background jobs
* `BackgroundThread` (task queue + workers, `schedule()`/`scheduleRepeating()`), `Worker`, `ObjectQueue`, `RepeatingTask`. Per-DB workers: `velocity`, `sql`, `sqlRepeating`, `import`, `startAutoImport`, `saveLinkingDictionary`, `loadLinkingDictionary`, `git_pull`, `index`.

### `objects/` + `geneology/` — family/GEDCOM domain (**no Python equivalent yet**)
* `Person`, `Family`, `FamilyNode`, `PersonFamilies`, `Rfamily`, `Rchild`, `Relation`.
* **`FamilyManagement`** (families/consorts/children from relations; family tree + GEDCOM ids), **`GedComProcessing`** (GEDCOM string/XML/print, XSLT), `gedcom/` (GEDCOM 6.0 record classes), `stylesheets/` (XSLT).

* `MHK2019.java` — standalone CLI (installer, user management, password hashing). *Partially replaced by `timelink/mhk/utilities.py` + `mhk` docker manager.*

## D. Database schema (`idb/etc/db/system/`, MySQL)

**Core** (Python equivalents exist in `timelink/api/models/`):
`entities` (id, class, inside, the_order, the_level, the_line, groupname, updated, indexed), `persons`, `attributes` (entity, the_type, the_value, the_date, obs), `relations` (origin, destination, ...), `acts`, `sources` (kleiofile, replaces), `objects`, `classes`/`class_attributes`, `rentities` (id, the_class, description, status, user), `rpersons` (seq, sname, sex, status, user), `robjects`, `links` (rid, instance, rule, lstatus), `geoentities`/`rgeoentities`/`geometries`/`geometries_entities`.

**System**: `syspar` (key/value params incl. linking `rl.*`), `syslog`, `sysout`.

**Full-text search**: `entitiesindex` (id, class, `description` FULLTEXT, first_date, last_date) — **not Lucene**; maintained by `IndexWorker` rendering each entity through `entity_description.vm`.

**Record linking** (see [record-linking-port.md](record-linking-port.md)): `lgraphs`, `candidates`, `ledges`, `link_queue`, `linklog`, `rel_equivalences`, `value_info`/`nvalue_info`/`attribute_info` caches, `rp_scores` + ~90 stored procedures.

**Families**: `rfamily`, `rchildren`, views `family_triplets*`. **Networks**: `nodes`, `edges`. **Caching**: `atr_stats`, `func_stats`, `rel_stats`, `place_stats`. **Views**: `irels`, `rirels`, `rrirels`, `lpersons`, `nfuncs` (advanced search), `nrels`, `nattributes`, `rnfuncs`, `casais`.

**Users DB (`mhk_users`)**: `users` (username, password, firstname, lastname, active, code), `comments` (db_name, entity_id, user_name, title, text, created).

Note: no `kleiofiles` table in the Java codebase (only `sources.kleiofile` column); timelink-py does have `kleiofiles` — keep the Python version.

## E. Kleio server interface (JSON-RPC, jsonrpc4j)

Default endpoint `http://localhost:8088/json/` (property
`mhk.kleio.service[.USER]`). Auth by tokens: admin token from
`KLEIO_ADMIN_TOKEN` env, or files/properties under
`mhk-home/system/conf/`; per-user tokens via
`generateServiceTokenForUser`.

Methods (`KleioService.java`): `directories_get`, `translations_get`,
`translations_translate(path, token, [structure,] echo, spawn)`,
`tokens_generate`, `users_invalidate`, `versions_get_global_status`,
`versions_get_remotes_branches`, `versions_pull`, `versions_push`,
`versions_commit`, `versions_get_user_info`, `versions_set_user_info`,
`versions_reset`, `identifications_get` (unused).

## F. Authentication, authorization, misc

* **Auth**: (1) `mhk-home/users/USER/conf/pwd` PBKDF2 hash of
  `username+password`; (2) property `mhk.user.password.USER`; (3)
  `mhk_users.users` table (public signup + emailed code + captcha).
  Session attribute `userID`; "default user" fallback; login tokens
  (`utoken` URL param) for bookmarks.
* **Authorization**: numeric `userLevel` (1 browse / 2 identifier / 3
  admin), from `mhk.user.level.USER` or per-DB `mhk.<db>.level.USER`;
  enforced in dispatch if-chain AND inside templates (`#if($level>1)`).
  Per-user DB whitelist `mhk.dbnames.USER`.
* **Search index**: `IndexWorker` repeating task — selects ≤100 rows
  `entities where updated > indexed`, renders `entity_description.vm`
  into text, replaces `entitiesindex` row, stamps `indexed`.
  Per-user toggle `mhk.indexing.USER`; `index_control.vm` UI.
* **Scheduled tasks**: `DoScheduleTask` enqueues arbitrary tasks into
  per-DB `BackgroundThread`; auto-import (delay
  `mhk.import.auto.delay.USER`), auto-index (100s), auto git pull;
  first-use DB bootstrap runs `etc/db/system` + `startup` scripts.
* **Security watchpoint**: templates and `ShowQuery` concatenate
  request params into SQL and `query_show.vm` renders arbitrary user
  SQL — the Python port must parameterize and gate this.
* **Deprecated in Java**: in-process Prolog workers (replaced by Kleio
  server), local `FileSystem` access, template dirs `alt/`/`old/`,
  `persons.vm` mockup, `DoSQL`, `ConnectionManager`.
