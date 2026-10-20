# MHK live instance — UX walkthrough

Walkthrough of the running Java MHK instance captured 2026-10-16,
for the NiceGUI rebuild. Instance:
`https://linode.timelink-mhk.net/mhk/` (Timelink 5.5 build 2238,
Tomcat 7), user `beta-tester` (level 3), database **`beta_tester_db`**
(sources `sources/ilhavo-beta`: Ílhavo parish baptisms/marriages/
burials 1875–1910, ~140 sources, 137,547 persons, 276,674 relations,
230,457 attributes; 2 real persons, 4 linked occurrences, 137,543
unlinked). Screenshots in [screenshots/](screenshots/).

Conventions observed on every page: top bar with database name +
build, user greeting, **level-gated nav** (LOGIN SEARCH EXPLORE
CALENDAR LINKING NETWORKS XTRAS SOURCES SYSTEM HELP), footer with
About/Terms + build link. Pretty URLs `/mhk/{db}/id/{id}`,
`/mhk/{db}/show/{action}`, `/mhk/{db}/exec/{script}`.

## 1. Search home & results — 01/02-*.png

* Home: full-text box (multi-word; `+maria` boolean), entity-type
  radios (All / Real Person / Person / Act) shown as radios, then a
  **select** on the results page; date interval (year / year-month /
  year-month-day); links to Advanced search and SQL search. Last
  comments block.
* Results: `Showing 0-50 of 2051`, results table **Id | Entity |
  Description** — description is the rendered `entity_description.vm`
  text (e.g. `bap n: maria sex: f. ( ... ) pai:maria ...`), each Id
  links to `/id/{id}`. Next/prev pagination (50/page).

## 2. Entity display

### Act (03-act-show.png)
Raw Kleio-style rendering: act header line
(`bap$ b1875.1 /ref=... /date=18750101 /loc=... /type=bap`), then
nested groups indented: persons (`n$ maria /sex=f /id=b1875.1-per1`),
their attributes (`ls$ profissao / carpinteiro / 1875-01-01`) and
relations (`rel$parentesco/pai /maria/ b1875.1-per1`). **Everything is
hyperlinked**: act type → acts query; person names → person query by
name; person ids → entity page; attribute types → `attribute_type`
query; values → `attribute_value` query. Comments form below.

### Occurrence person (04-person-show.png, 19-person-linked.png)
Header: name, id, groupname (n/pad/…), sex, line number; if linked:
**`Full file (RID) : rp-1`**. Actions:
* **Unlink** form (hidden action=unlink, rid, personid).
* **Same as / Link** form: free text (rid or name) →
  `rperson_preview.vm` confirmation.
* **IDList mechanism**: "save id" stores occurrence ids in a cookie;
  every page carries a persistent form `Link preview` →
  `rentity_preview.vm` + `Empty list` button — this is how batch
  linking is done across searches.
* PERSON INFO table: **YEAR | FUNCTION | ATTRIBUTES | RELATIONS |
  NAME** — one row per act participation; function = `bap : pad`
  (act-type : role); attributes listed as `type : Value`; relations
  rendered in natural language (`tem como pai: jacinto tavares
  pinto`, and for linked persons `same as de sebastiao antonio da
  silva`). Comments form.

### Real person (07-rperson-show.png)
Header: name, `id: rp-1 user: beta-tester status: N sex: m seq: 1
Obs:`. Tabs: **REAL PERSON INFO | ALL THE ACTS | RELATED PERSONS |
IDENTIFICATIONS** (+ `* Robot identifications` filter, `RPERSON.FAMILY`
tab appears on identifications page). Main tab merges all linked
occurrences into the same YEAR|FUNCTION|ATTRIBUTES|RELATIONS|NAME
table — the "reconstructed biography" view. Name → persons-by-name
query; tabs → `rperson_acts.vm`, `rperson_related.vm`,
`rperson_identification.vm` with `rid` param.

### Identifications tab (08-rperson-identifications.png)
`* Users that identified this person=[beta-tester]`; table **YEAR |
ID | SAFE RID | BETA-TESTER * | FUNCTION | ATTRIBUTES | RELATIONS |
NAME** — one row per linked occurrence with a **checkbox per row**
(`personid` values), buttons **"Make selected entries the same"**
(→ `rperson_preview.vm` preview → sameas commit), **Select all /
Unselect all**. This plus Unlink on the person page is the entire
manual linking loop.

## 3. Linking dashboard — 05-linking.png, 06-linking-show.png

Tabs **Status | Export | Import**:
* Status: table **USER NAME | USER.REAL.ENTITIES | OCCURRENCES
  LINKED | UNLINKED OCCURRENCES** per user (beta-tester: 2 / 4 /
  137543); "Identifications by other users" section; global status
  sentence; **diagnostics table** (Real Entities with 0 occurrences,
  with non-existing occurrences — global and per user).
* Export: "Export current user identifications" (`saveldict&user=`),
  "Export all users identification" (`user=*`).
* Import: form `loadldict` listing identification files found in the
  sources tree (here `identifications/mhk_identification.json`,
  `mhk_identification_ilhavo.cli`, `.err`) with a checkbox each.

## 4. Sources (translate/import/git) — 09..11-*.png

Tabs **SOURCE FILES | REPOSITORY | TRANSLATION OUTPUT | IMPORTER
OUTPUT | HELP**:
* Directory tree of the sources root with subdir links; status panel
  always visible on the right: RECENT CHANGES (Need translation N,
  Need import N), REVIEW NEEDED (translation errors, translation
  warnings + See list, import errors), IN PROCESS (translating,
  queued translation, queued import). Auto-refreshes.
* Per-directory file table: status flag (**[V]** green / **[W]**
  warning — colored in UI), name (→ source file viewer), translation
  date, **translation report** ("0 Errors. 1 Warnings" → `.rpt`
  viewer), **import report** ("0 ERRORS" → `.xrpt` viewer). Per-file
  `TRANSLATE_n` / `IMPORT_n` checkboxes feed a **batch processfiles**
  form (translate then import selected).
* Repository tab: "N LOCAL CHANGES NOT SAVED (COMMITTED)" counter,
  git identity form (name/email, `user-info`), LAST LOCAL COMMITS
  list (relative date, message, author), remote tracking status
  banner; commit/push/pull/revert buttons appear with pending
  changes.

## 5. System — 12-system.png

Current task, queued tasks (with thread status), messages from tasks
(e.g. `call update_cache()` → `UPDATE 130662`), errors; database
statistics (entity counts per class + **entities on index: 2516**);
full listing of `mhk.*` servlet attributes (per-user dbname, sources
dir, level; kleio API scopes per level: level2=`sources`,
level3=`sources,files,structures,translations,upload,delete,mkdir`).

## 6. Explore / Calendar / Advanced search — 13..15-*.png

* Explore: "ID of something" direct-lookup box; **Names A–Z** letter
  browser; **Attributes with counts** (each → value browse/search);
  **Functions with counts** (mad 14513, mae 14547, n 14553, pai
  14510 …) — this page is the data-driven "facet" entry into the DB.
* Calendar: 12 month-grids (day cells presumably link to acts).
* Advanced search: name box (quoted = exact), time interval, **up to
  6 attribute type/value pairs** with type dropdowns populated from
  the DB attribute list.

## 7. SQL query — 17-sql-query.png

Textarea (default `SELECT * FROM persons LIMIT 10`), Execute; lists
all searchable tables/views (including linking tables `ledges`,
`link_queue`, `rel_equivalences`, `links`, stats caches, family
views). Results table supports click-two-rows range selection.

## 8. Networks — 18-networks.png

Existing networks table (Network | Nodes | Not Visited | Edges | To
Be Linked | View | Export); generation form: network id, relation
type (parentesco/profissional/sociabilidade), value (%=all),
direction (direct/inverse/both), date range — submitted as a
**background scheduled task** (`action=schedule task=velocity
template=scripts/GenerateNetwork.vm`); page self-refreshes while
generating ("when not visited equals 0 the network has been
generated"); exports to **Guess (.gdf) and Pajek (.net)**.

## 9. Xtras — 16-xtras.png

500 NullPointerException on this install (no xtras template pack
configured) — known fragility of the optional-packs mechanism.

## Notes for the NiceGUI rebuild

1. The **IDList cookie + "Link preview" on every page** pattern is
   MHK's answer to cross-page selection for batch linking; in
   NiceGUI a server-side "cart" per session is simpler and safer —
   keep the workflow (mark occurrences anywhere → preview → commit),
   drop the cookie.
2. **Everything-is-a-link** (attribute type/value, relation names,
   function roles) is the defining UX of MHK pages; the NiceGUI
   `display_id_page` should reproduce these as links into
   parametrized searches.
3. The **YEAR|FUNCTION|ATTRIBUTES|RELATIONS|NAME** table is the
   universal person/rperson presentation — one component serves
   person_show, rperson_show, rperson_acts, identifications.
4. Sources page status panel (need translation / need import /
   errors / warnings / in-process) maps 1:1 onto the existing
   NiceGUI sources page counters — extend it with per-file
   TRANSLATE/IMPORT checkboxes (already exists) + report viewers.
5. Networks page shows how long-running generation should work:
   background job + progress counters + export links; matches the
   APScheduler pattern already in the webapp.
6. Robot identifications are a first-class filter (`* Robot
   identifications`, `rule='*robot'` links) — the port must keep
   link provenance visible.
